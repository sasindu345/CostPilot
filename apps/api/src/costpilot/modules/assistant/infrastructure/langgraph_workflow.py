"""The supervisor and its specialists, as a LangGraph graph.

The supervisor uses one AI call to choose a route. Specialists are plain code that runs safe tools,
which keeps each question to two AI calls at most.
"""

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from costpilot.modules.assistant.application.ports import ChatModel
from costpilot.modules.assistant.application.workspace_tools import WorkspaceTools
from costpilot.modules.assistant.domain.models import Evidence, Route

SUPERVISOR = "supervisor"
SPECIALISTS = {
    Route.COST: "cost_specialist",
    Route.ANOMALY: "anomaly_specialist",
    Route.OPTIMIZATION: "optimization_specialist",
    Route.OUT_OF_SCOPE: "out_of_scope",
}


class State(TypedDict, total=False):
    question: str
    tools: WorkspaceTools
    route: Route
    evidence: Evidence


class LangGraphEvidenceWorkflow:
    def __init__(self, model: ChatModel) -> None:
        self._model = model
        self._graph = self._build()

    async def gather(self, question: str, tools: WorkspaceTools) -> Evidence:
        state = await self._graph.ainvoke({"question": question, "tools": tools})
        return state["evidence"]

    def _build(self):
        graph = StateGraph(State)
        graph.add_node(SUPERVISOR, self._supervise)
        graph.add_node(SPECIALISTS[Route.COST], self._cost)
        graph.add_node(SPECIALISTS[Route.ANOMALY], self._anomaly)
        graph.add_node(SPECIALISTS[Route.OPTIMIZATION], self._optimize)
        graph.add_node(SPECIALISTS[Route.OUT_OF_SCOPE], self._decline)
        graph.add_edge(START, SUPERVISOR)
        graph.add_conditional_edges(SUPERVISOR, lambda state: SPECIALISTS[state["route"]])
        for name in SPECIALISTS.values():
            graph.add_edge(name, END)
        return graph.compile()

    async def _supervise(self, state: State) -> State:
        return {"route": await self._model.choose_route(state["question"])}

    async def _cost(self, state: State) -> State:
        return {"evidence": await state["tools"].cost_evidence()}

    async def _anomaly(self, state: State) -> State:
        return {"evidence": await state["tools"].anomaly_evidence()}

    async def _optimize(self, state: State) -> State:
        return {"evidence": await state["tools"].optimization_evidence(state["question"])}

    async def _decline(self, _: State) -> State:
        return {"evidence": Evidence(Route.OUT_OF_SCOPE)}
