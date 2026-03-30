"""LangGraph graph definition for the 3-agent debate system."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from .nodes import (
    aggregator_node,
    factcheck_node,
    optimist_node,
    orchestrator_node,
    suspicion_node,
)
from .state import DebateState


def build_debate_graph() -> StateGraph:
    """
    Build the debate graph with fan-out / fan-in topology:

    START → orchestrator → ┬─ suspicion  ─┬→ aggregator → END
                           ├─ optimist   ─┤
                           └─ factcheck  ─┘
    """
    builder = StateGraph(DebateState)

    # Add nodes
    builder.add_node("orchestrator", orchestrator_node)
    builder.add_node("suspicion", suspicion_node)
    builder.add_node("optimist", optimist_node)
    builder.add_node("factcheck", factcheck_node)
    builder.add_node("aggregator", aggregator_node)

    # Edges: START → orchestrator
    builder.add_edge(START, "orchestrator")

    # Fan-out: orchestrator → 3 agents in parallel
    builder.add_edge("orchestrator", "suspicion")
    builder.add_edge("orchestrator", "optimist")
    builder.add_edge("orchestrator", "factcheck")

    # Fan-in: all 3 → aggregator
    builder.add_edge("suspicion", "aggregator")
    builder.add_edge("optimist", "aggregator")
    builder.add_edge("factcheck", "aggregator")

    # aggregator → END
    builder.add_edge("aggregator", END)

    return builder.compile()


# Singleton compiled graph
debate_graph = build_debate_graph()
