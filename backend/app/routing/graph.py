from collections.abc import Callable
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.memory.store import ScopedMemory
from app.routing.router import Router
from app.services.runtime import AgentResult, AgentRuntime, EventSink
from app.tools.registry import BoundTools


class GraphState(TypedDict, total=False):
    message: str
    agent: str | None
    outcome: AgentResult
    emit: EventSink


def build_graph(
    router: Router,
    runtimes: dict[str, AgentRuntime],
    bind_tools: Callable[[str, str, EventSink], BoundTools],
    bind_memory: Callable[[str], ScopedMemory],
):
    graph = StateGraph(GraphState)

    def route(state: GraphState) -> GraphState:
        agent = router.select(state["message"])
        state["emit"](agent, "routing", None, None, "selected" if agent else "clarification", f"Selected {agent}." if agent else "Request needs a domain clarification.")
        if agent is None:
            return {"agent": None, "outcome": AgentResult("Is this for HenHacks sponsorship or CS+Social Good?", clarification=True)}
        return {"agent": agent}

    def delegate(state: GraphState) -> GraphState:
        agent = state["agent"]
        if agent is None:
            raise ValueError("Cannot delegate without selected agent")
        runtime = runtimes[agent]
        outcome = runtime.run(
            state["message"],
            lambda skill: bind_tools(agent, skill, state["emit"]),
            bind_memory(runtime.manifest.memory_namespace),
            state["emit"],
        )
        return {"outcome": outcome}

    graph.add_node("route", route)
    graph.add_node("delegate", delegate)
    graph.add_edge(START, "route")
    graph.add_conditional_edges("route", lambda state: "delegate" if state["agent"] else END)
    graph.add_edge("delegate", END)
    return graph.compile()
