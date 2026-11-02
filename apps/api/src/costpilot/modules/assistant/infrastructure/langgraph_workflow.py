"""The supervisor and its specialists, as a LangGraph graph.

The supervisor uses one AI call to choose the routes. If a question needs several specialists,
LangGraph runs them in parallel. Specialists are plain code that runs safe tools, and a final
step joins their evidence, so each question uses two AI calls at most.
"""

from operator import add
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

from costpilot.modules.assistant.application.ports import ChatModel
from costpilot.modules.assistant.application.workspace_tools import WorkspaceTools
from costpilot.modules.assistant.domain.merge import merge_evidence
from costpilot.modules.assistant.domain.models import Evidence, Route

SUPERVISOR = "supervisor"
JOIN = "join_evidence"
SPECIALISTS = {
    Route.COST: "cost_specialist",
    Route.ANOMALY: "anomaly_specialist",
    Route.OPTIMIZATION: "optimization_specialist",
    Route.OUT_OF_SCOPE: "out_of_scope",
}


class State(TypedDict, total=False):
    question: str
    tools: WorkspaceTools
    routes: list[Route]
    # `add` keeps every specialist's result when parallel steps finish together.
    found: Annotated[list[Evidence], add]
    evidence: Evidence


class LangGraphEvidenceWorkflow:
    def __init__(self, model: ChatModel) -> None:
        self._model = model
        self._graph = self._build()

    async def gather(self, question: str, tools: WorkspaceTools) -> Evidence:
        state = await self._graph.ainvoke({"question": question, "tools": tools, "found": []})
        return state["evidence"]

    def _build(self):
        graph = StateGraph(State)
        graph.add_node(SUPERVISOR, self._supervise)
        graph.add_node(SPECIALISTS[Route.COST], self._cost)
        graph.add_node(SPECIALISTS[Route.ANOMALY], self._anomaly)
        graph.add_node(SPECIALISTS[Route.OPTIMIZATION], self._optimize)
        graph.add_node(SPECIALISTS[Route.OUT_OF_SCOPE], self._decline)
        graph.add_node(JOIN, self._join)
        graph.add_edge(START, SUPERVISOR)
        graph.add_conditional_edges(
            SUPERVISOR, self._choose_specialists, list(SPECIALISTS.values())
        )
        for name in SPECIALISTS.values():
            graph.add_edge(name, JOIN)
        graph.add_edge(JOIN, END)
        return graph.compile()

    async def _supervise(self, state: State) -> State:
        return {"routes": await self._model.choose_routes(state["question"])}

    def _choose_specialists(self, state: State) -> list[str]:
        """Returning several names is what makes LangGraph run them at the same time."""
        return [SPECIALISTS[route] for route in state["routes"]]

    async def _cost(self, state: State) -> State:
        return {"found": [await state["tools"].cost_evidence()]}

    async def _anomaly(self, state: State) -> State:
        return {"found": [await state["tools"].anomaly_evidence()]}

    async def _optimize(self, state: State) -> State:
        return {"found": [await state["tools"].optimization_evidence(state["question"])]}

    async def _decline(self, _: State) -> State:
        return {"found": [Evidence((Route.OUT_OF_SCOPE,))]}

    async def _join(self, state: State) -> State:
        return {"evidence": merge_evidence(state["found"])}
