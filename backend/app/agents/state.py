"""LangGraph state definition for the debate system."""

from __future__ import annotations

from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class AgentOpinionState(TypedDict):
    opinion: str
    confidence: float
    signals: list[str]


class DebateState(TypedDict):
    # Input
    evidence: dict  # Serialized EvidenceBundle
    topic: str  # Analysis topic/focus
    user_question: str | None  # Optional follow-up question

    # Orchestrator output
    analysis_focus: str  # Key points to explore

    # Agent outputs
    suspicion_opinion: AgentOpinionState | None
    optimist_opinion: AgentOpinionState | None
    factcheck_opinion: AgentOpinionState | None

    # Aggregated output
    followup_questions: list[str]
    debate_summary: str | None
