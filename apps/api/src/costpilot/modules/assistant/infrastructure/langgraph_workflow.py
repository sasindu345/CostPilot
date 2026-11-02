"""The supervisor and its specialists, as a LangGraph graph.

The supervisor chooses only the specialists a question needs, and LangGraph runs them in parallel.
Documents are fetched once, before the specialists start. Python does the calculations first, and
an AI specialist only runs where reasoning adds something.
"""

from operator import add
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

from costpilot.modules.assistant.application.ports import ChatModel
from costpilot.modules.assistant.application.specialists import (
    ANOMALY,
    KNOWLEDGE,
    OPTIMIZATION,
    SpecialistAgents,
)
from costpilot.modules.assistant.application.workspace_tools import WorkspaceTools
from costpilot.modules.assistant.domain.merge import merge_evidence
from costpilot.modules.assistant.domain.metrics import AnswerMeter
from costpilot.modules.assistant.domain.models import DocumentPassage, Evidence, Route, RoutePlan

SUPERVISOR = "supervisor"
RETRIEVE = "retrieve_documents"
JOIN = "join_evidence"
SPECIALISTS = {
    Route.COST: "cost_specialist",
    Route.ANOMALY: "anomaly_specialist",
    Route.OPTIMIZATION: "optimization_specialist",
    Route.KNOWLEDGE: "knowledge_specialist",
    Route.OUT_OF_SCOPE: "out_of_scope",
}
NEEDS_DOCUMENTS = {Route.OPTIMIZATION, Route.KNOWLEDGE}


class State(TypedDict, total=False):
    question: str
    tools: WorkspaceTools
    meter: AnswerMeter
    plan: RoutePlan
    documents: list[DocumentPassage]
    search_limits: list[str]
    # `add` keeps every specialist's result when parallel steps finish together.
    found: Annotated[list[Evidence], add]
    evidence: Evidence


class LangGraphEvidenceWorkflow:
    def __init__(self, model: ChatModel, agents: SpecialistAgents) -> None:
        self._model = model
        self._agents = agents
        self._graph = self._build()

    async def gather(self, question: str, tools: WorkspaceTools, meter: AnswerMeter) -> Evidence:
        state = await self._graph.ainvoke(
            {"question": question, "tools": tools, "meter": meter, "found": []}
        )
        return state["evidence"]

    def _build(self):
        graph = StateGraph(State)
        graph.add_node(SUPERVISOR, self._supervise)
        graph.add_node(RETRIEVE, self._retrieve)
        graph.add_node(SPECIALISTS[Route.COST], self._cost)
        graph.add_node(SPECIALISTS[Route.ANOMALY], self._anomaly)
        graph.add_node(SPECIALISTS[Route.OPTIMIZATION], self._optimize)
        graph.add_node(SPECIALISTS[Route.KNOWLEDGE], self._knowledge)
        graph.add_node(SPECIALISTS[Route.OUT_OF_SCOPE], self._decline)
        graph.add_node(JOIN, self._join)
        graph.add_edge(START, SUPERVISOR)
        graph.add_edge(SUPERVISOR, RETRIEVE)
        graph.add_conditional_edges(RETRIEVE, self._choose_specialists, list(SPECIALISTS.values()))
        for name in SPECIALISTS.values():
            graph.add_edge(name, JOIN)
        graph.add_edge(JOIN, END)
        return graph.compile()

    async def _supervise(self, state: State) -> State:
        with state["meter"].step(SUPERVISOR):
            return {"plan": await self._model.choose_routes(state["question"], state["meter"])}

    async def _retrieve(self, state: State) -> State:
        plan = state["plan"]
        if not NEEDS_DOCUMENTS & set(plan.routes):
            return {"documents": [], "search_limits": []}
        with state["meter"].step(RETRIEVE):
            documents, limits = await state["tools"].search_documents(
                state["question"], plan.provider
            )
        return {"documents": documents, "search_limits": limits}

    def _choose_specialists(self, state: State) -> list[str]:
        """Returning several names is what makes LangGraph run them at the same time."""
        return [SPECIALISTS[route] for route in state["plan"].routes]

    async def _cost(self, state: State) -> State:
        with state["meter"].step(SPECIALISTS[Route.COST]):
            return {"found": [await state["tools"].cost_evidence()]}

    async def _anomaly(self, state: State) -> State:
        tools, meter = state["tools"], state["meter"]
        with meter.step(SPECIALISTS[Route.ANOMALY]):
            evidence = await tools.anomaly_evidence()
            has_detail = await tools.has_line_detail()
        # Without something unusual and line detail, the AI could only guess, so it is not called.
        if evidence.findings and has_detail:
            evidence = await self._agents.add_findings(ANOMALY, state["question"], evidence, meter)
        return {"found": [evidence]}

    async def _optimize(self, state: State) -> State:
        meter = state["meter"]
        with meter.step(SPECIALISTS[Route.OPTIMIZATION]):
            evidence = await state["tools"].optimization_evidence(
                state["documents"], state["search_limits"]
            )
        if evidence.passages:
            evidence = await self._agents.add_findings(
                OPTIMIZATION, state["question"], evidence, meter
            )
        return {"found": [evidence]}

    async def _knowledge(self, state: State) -> State:
        evidence = state["tools"].knowledge_evidence(state["documents"], state["search_limits"])
        if evidence.passages:
            evidence = await self._agents.add_findings(
                KNOWLEDGE, state["question"], evidence, state["meter"]
            )
        return {"found": [evidence]}

    async def _decline(self, _: State) -> State:
        return {"found": [Evidence((Route.OUT_OF_SCOPE,))]}

    async def _join(self, state: State) -> State:
        return {"evidence": merge_evidence(state["found"])}
