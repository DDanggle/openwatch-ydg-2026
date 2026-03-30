"""LangGraph node functions for the debate system."""

from __future__ import annotations

import json
import re

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from ..config import settings
from .guardrails import apply_guardrails
from .prompts import (
    AGGREGATOR_PROMPT,
    FACTCHECK_PROMPT,
    OPTIMIST_PROMPT,
    ORCHESTRATOR_PROMPT,
    SUSPICION_PROMPT,
)
from .state import DebateState

_llm = None


def _get_llm() -> BaseChatModel:
    global _llm
    if _llm is None:
        if settings.openai_api_key:
            from langchain_openai import ChatOpenAI
            _llm = ChatOpenAI(
                model=settings.openai_model,
                openai_api_key=settings.openai_api_key,
                max_tokens=2000,
                temperature=0.7,
            )
        elif settings.anthropic_api_key:
            from langchain_anthropic import ChatAnthropic
            _llm = ChatAnthropic(
                model="claude-sonnet-4-20250514",
                anthropic_api_key=settings.anthropic_api_key,
                max_tokens=2000,
                temperature=0.7,
            )
        else:
            raise RuntimeError("No LLM API key configured (set OPENAI_API_KEY or ANTHROPIC_API_KEY)")
    return _llm


def _format_evidence(evidence: dict) -> str:
    """Format evidence bundle as readable text for the LLM."""
    lines: list[str] = []
    lines.append(f"## 의원 정보")
    lines.append(f"- 이름: {evidence.get('politician_name', '알 수 없음')}")
    lines.append(f"- 정당: {evidence.get('party', '')}")
    lines.append(f"- 지역구: {evidence.get('district', '')}")

    # Timeline
    timeline = evidence.get("timeline", [])
    if timeline:
        lines.append(f"\n## 자산 추이 ({len(timeline)}년간)")
        for entry in timeline:
            lines.append(
                f"- {entry['year']}년: "
                f"총 {entry.get('total_amount', 0):,}원 "
                f"(순자산 {entry.get('net_amount', 0):,}원)"
            )
            breakdown = entry.get("breakdown_by_type", {})
            if breakdown:
                parts = [f"{k}: {v:,}원" for k, v in breakdown.items() if v > 0]
                if parts:
                    lines.append(f"  구성: {', '.join(parts)}")
            family = entry.get("breakdown_by_family", {})
            if family:
                parts = [f"{k}: {v:,}원" for k, v in family.items() if v > 0]
                if parts:
                    lines.append(f"  소유: {', '.join(parts)}")

    # Significant changes
    changes = evidence.get("significant_changes", [])
    if changes:
        lines.append(f"\n## 주요 변동 사건 ({len(changes)}건)")
        for c in changes[:10]:
            lines.append(
                f"- {c['year']}년 {c['category']} ({c['relation']}): "
                f"{c.get('change_amount', 0):+,}원 "
                f"({c.get('change_pct', 0):+.1f}%)"
            )
            if c.get("description"):
                lines.append(f"  상세: {c['description']}")

    # Metrics
    metrics = evidence.get("metrics", {})
    if metrics:
        lines.append(f"\n## 분석 지표")
        if metrics.get("cagr") is not None:
            lines.append(f"- CAGR: {metrics['cagr']:.2f}%")
        lines.append(f"- 총 증가액: {metrics.get('absolute_growth', 0):,}원")
        lines.append(f"- 증가율: {metrics.get('growth_rate', 0):.1f}%")
        lines.append(
            f"- 가족 기여도: {metrics.get('family_contribution_ratio', 0):.1%}"
        )
        lines.append(
            f"- 배우자 비중: {metrics.get('spouse_contribution_ratio', 0):.1%}"
        )
        lines.append(
            f"- 부동산 비중: {metrics.get('real_estate_share', 0):.1%}"
        )
        if metrics.get("avg_gap_pct") is not None:
            lines.append(f"- 부동산 괴리율(평균): {metrics['avg_gap_pct']:.1f}%")
        flags = metrics.get("anomaly_flags", {})
        if flags:
            triggered = [k for k, v in flags.items() if v]
            if triggered:
                lines.append(f"- 이상 징후: {', '.join(triggered)}")
        lines.append(
            f"- 이상치 점수: {metrics.get('anomaly_score', 0):.1f}/100"
        )

    return "\n".join(lines)


def _extract_confidence(text: str) -> float:
    """Extract confidence score from agent output."""
    match = re.search(r"신뢰도[:\s]*(\d+\.?\d*)", text)
    if match:
        return min(float(match.group(1)), 1.0)
    return 0.5


async def orchestrator_node(state: DebateState) -> dict:
    """Analyze evidence and set analysis focus."""
    llm = _get_llm()
    evidence_text = _format_evidence(state["evidence"])
    topic = state.get("topic", "전체 분석")
    user_q = state.get("user_question")

    prompt = ORCHESTRATOR_PROMPT.format(topic=topic)
    if user_q:
        prompt += f"\n\n## 사용자 추가 질문\n{user_q}"

    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content=f"다음 데이터를 분석하세요:\n\n{evidence_text}"),
    ]

    response = await llm.ainvoke(messages)
    return {"analysis_focus": response.content}


async def suspicion_node(state: DebateState) -> dict:
    """의심 탐정 analysis."""
    llm = _get_llm()
    evidence_text = _format_evidence(state["evidence"])
    prompt = SUSPICION_PROMPT.format(analysis_focus=state["analysis_focus"])

    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content=evidence_text),
    ]

    response = await llm.ainvoke(messages)
    cleaned = apply_guardrails(response.content, "suspicion")

    return {
        "suspicion_opinion": {
            "opinion": cleaned,
            "confidence": _extract_confidence(cleaned),
            "signals": [],
        }
    }


async def optimist_node(state: DebateState) -> dict:
    """낙관적 분석가 analysis."""
    llm = _get_llm()
    evidence_text = _format_evidence(state["evidence"])
    prompt = OPTIMIST_PROMPT.format(analysis_focus=state["analysis_focus"])

    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content=evidence_text),
    ]

    response = await llm.ainvoke(messages)
    cleaned = apply_guardrails(response.content, "optimist")

    return {
        "optimist_opinion": {
            "opinion": cleaned,
            "confidence": _extract_confidence(cleaned),
            "signals": [],
        }
    }


async def factcheck_node(state: DebateState) -> dict:
    """팩트체커 analysis."""
    llm = _get_llm()
    evidence_text = _format_evidence(state["evidence"])
    prompt = FACTCHECK_PROMPT.format(analysis_focus=state["analysis_focus"])

    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content=evidence_text),
    ]

    response = await llm.ainvoke(messages)
    cleaned = apply_guardrails(response.content, "factcheck")

    return {
        "factcheck_opinion": {
            "opinion": cleaned,
            "confidence": _extract_confidence(cleaned),
            "signals": [],
        }
    }


async def aggregator_node(state: DebateState) -> dict:
    """Collect all opinions and generate follow-up questions."""
    llm = _get_llm()

    suspicion = (state.get("suspicion_opinion") or {}).get("opinion", "없음")
    optimist = (state.get("optimist_opinion") or {}).get("opinion", "없음")
    factcheck = (state.get("factcheck_opinion") or {}).get("opinion", "없음")

    prompt = AGGREGATOR_PROMPT.format(
        suspicion=suspicion,
        optimist=optimist,
        factcheck=factcheck,
    )

    messages = [
        SystemMessage(content="당신은 토론 정리자입니다."),
        HumanMessage(content=prompt),
    ]

    response = await llm.ainvoke(messages)

    # Parse follow-up questions
    questions: list[str] = []
    for line in response.content.strip().split("\n"):
        line = line.strip()
        if re.match(r"^\d+[.\)]\s*", line):
            q = re.sub(r"^\d+[.\)]\s*", "", line).strip()
            if q:
                questions.append(q)

    return {
        "followup_questions": questions[:3],
        "debate_summary": None,
    }
