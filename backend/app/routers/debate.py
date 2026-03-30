"""Debate API endpoints with SSE streaming — 댓글 스타일 에이전트."""

from __future__ import annotations

import asyncio
import json
import logging
import random
from collections.abc import AsyncGenerator

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from ..agents.guardrails import DISCLAIMER
from ..config import settings
from ..models.schemas import AgentOpinion, DebateRequest, DebateResult, FollowupRequest
from ..services.evidence_bundle import build_evidence_bundle

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/debate", tags=["debate"])

AGENT_DISPLAY = {
    "suspicion": {"name": "파란장미", "emoji": "🌹", "label": "민주당 지지자 AI"},
    "optimist": {"name": "태극기전사", "emoji": "🇰🇷", "label": "국민의힘 지지자 AI"},
    "factcheck": {"name": "논두렁회계사", "emoji": "🌾", "label": "중도 농부 AI"},
}


def _use_mock() -> bool:
    return not settings.anthropic_api_key and not settings.openai_api_key


def _build_mock_opinions(bundle_dict: dict, topic: str, user_question: str | None = None) -> dict:
    name = bundle_dict.get("politician_name", "이 의원")
    party = bundle_dict.get("party", "")
    metrics = bundle_dict.get("metrics", {})
    timeline = bundle_dict.get("timeline", [])

    cagr = metrics.get("cagr") or 0
    growth = metrics.get("absolute_growth", 0)
    family_ratio = metrics.get("family_contribution_ratio", 0)
    re_share = metrics.get("real_estate_share", 0)
    gap = metrics.get("avg_gap_pct") or 0
    anomaly = metrics.get("anomaly_score", 0)

    first_year = timeline[0]["year"] if timeline else "?"
    last_year = timeline[-1]["year"] if timeline else "?"
    first_eok = timeline[0].get("net_amount", 0) / 1_0000_0000 if timeline else 0
    last_eok = timeline[-1].get("net_amount", 0) / 1_0000_0000 if timeline else 0
    growth_eok = growth / 1_0000_0000

    is_opposition = "국민의힘" in (party or "")
    q_context = f'\n\n"{user_question}"에 대해서 말인데요... ' if user_question else ""

    # 🌹 파란장미 (민주당 지지자)
    if is_opposition:
        blue = f"""{q_context}{name} 의원 재산이 {first_year}년 {first_eok:.0f}억에서 {last_year}년 {last_eok:.0f}억??? ㅋㅋㅋ CAGR {cagr:.1f}%면 웬만한 펀드매니저보다 잘하는 건데요? 가족 명의 비중이 {family_ratio*100:.0f}%인 것도 좀... 이게 정상인가요 진짜? 부동산 신고가랑 시세 차이가 평균 {gap:.0f}%라는데 ㄹㅇ 이것도 설명 좀 해주셨으면. 국민은 월급 받아서 집 한 채 사기도 힘든데 어떻게 {growth_eok:.0f}억이 {last_year-first_year if isinstance(first_year, int) else 9}년 만에 늘어나는 건지 진심 궁금합니다 ^^

👍 {random.randint(250, 500)} 👎 {random.randint(20, 80)}"""
    else:
        blue = f"""{q_context}우리 {name} 의원님 재산 {last_eok:.0f}억... 솔직히 좀 많긴 한데ㅋㅋ 그래도 부동산이 {re_share*100:.0f}%잖아요. {first_year}~{last_year}년이면 서울 집값 다 올랐을 때고, CAGR {cagr:.1f}%면 시장 상승분 감안하면 뭐... 근데 가족 명의가 {family_ratio*100:.0f}%인 건 조금 아쉽네요. 더 투명했으면 좋겠어요. 그래도 적어도 국짐처럼 막 수백억 건물 사고 그러진 않잖아요? ㅎㅎ

👍 {random.randint(200, 400)} 👎 {random.randint(40, 120)}"""

    # 🇰🇷 태극기전사 (국민의힘 지지자)
    if is_opposition:
        red = f"""{q_context}아니 {name} 의원 재산이 {last_eok:.0f}억이 뭐가 문제입니까! 사업하고 투자 잘 한 거지! CAGR {cagr:.1f}%? 부동산 비중 {re_share*100:.0f}%면 그냥 집값 오른 거잖아요!! {first_year}년부터 {last_year}년까지 서울 아파트 안 오른 데가 어딨습니까! 능력 있는 사람이 재산 모으는 게 뭐가 잘못입니까!! 오히려 경제 잘 아는 분이 국회 가야죠!!!

👍 {random.randint(200, 400)} 👎 {random.randint(30, 90)}"""
    else:
        red = f"""{q_context}{name} 의원 재산 {last_eok:.0f}억?! {first_year}년엔 {first_eok:.0f}억이었다면서요?! {growth_eok:.0f}억이 어디서 뚝딱 나온 겁니까!! CAGR {cagr:.1f}%면 이건 뭐 주식 천재도 아니고!! 가족한테 {family_ratio*100:.0f}%나 넘기고!! 부동산 괴리율 {gap:.0f}%?? 이거 국세청에서 한번 들여다봐야 하는 거 아닌가요?! 국민 등쳐먹은 거 아닌지 설명 좀 해보시죠!!!

👍 {random.randint(250, 500)} 👎 {random.randint(20, 60)}"""

    # 🌾 논두렁회계사 (중도 팩트체커)
    farmer = f"""{q_context}허허, 두 분 다 열정이 대단하시유. 근데 숫자로만 보자면여...

{name} 의원 {first_year}→{last_year}년: {first_eok:.0f}억 → {last_eok:.0f}억 (CAGR {cagr:.1f}%)
- 부동산 비중: {re_share*100:.0f}% | 가족 명의: {family_ratio*100:.0f}%
- 부동산 괴리율: 평균 {gap:.0f}% (신고가 vs 추정 시세)
- 이상치 점수: {anomaly:.0f}/100

이건 뭐 {party} 의원이든 아니든, 숫자가 이러면 한번 들여다볼 필요는 있는 거여. 근데 이게 다 공시가격 기준이라 실제론 더 벌어질 수도 있고, 아닐 수도 있어유. 정당 가지고 싸우지 말고 숫자를 봐야쥬. 양쪽 다 재산 많은 의원은 넘쳐나유 ㅎㅎ

※ 공개 신고자료 기반 추정이니 참고만 하세유~

👍 {random.randint(400, 700)} 👎 {random.randint(5, 20)}"""

    followups = [
        f"{name} 의원 가족 중 배우자 재산이 제일 많이 변한 시점이 언제인가요?",
        f"같은 당 의원들이랑 비교하면 {name} 의원 재산 순위가 몇 등인가요?",
        f"부동산 말고 증권·예금 쪽 변동은 어떤가요? 주식으로도 벌었나요?",
    ]

    return {
        "suspicion": {"opinion": blue, "confidence": 0.72},
        "optimist": {"opinion": red, "confidence": 0.68},
        "factcheck": {"opinion": farmer, "confidence": 0.85},
        "followup_questions": followups,
    }


async def _stream_mock(bundle_dict: dict, topic: str, user_question: str | None = None) -> AsyncGenerator[dict, None]:
    mock = _build_mock_opinions(bundle_dict, topic, user_question)

    for agent_key in ["suspicion", "optimist", "factcheck"]:
        display = AGENT_DISPLAY[agent_key]
        opinion_text = mock[agent_key]["opinion"]
        confidence = mock[agent_key]["confidence"]

        yield {
            "event": "agent_start",
            "data": json.dumps({
                "agent": agent_key,
                "display_name": display["name"],
                "emoji": display["emoji"],
                "label": display["label"],
            }, ensure_ascii=False),
        }

        chunk_size = 15
        for i in range(0, len(opinion_text), chunk_size):
            yield {
                "event": "agent_token",
                "data": json.dumps({
                    "agent": agent_key,
                    "token": opinion_text[i:i + chunk_size],
                }, ensure_ascii=False),
            }
            await asyncio.sleep(0.02)

        yield {
            "event": "agent_done",
            "data": json.dumps({
                "agent": agent_key,
                "opinion": opinion_text,
                "confidence": confidence,
            }, ensure_ascii=False),
        }
        await asyncio.sleep(0.1)

    yield {
        "event": "debate_complete",
        "data": json.dumps({
            "followup_questions": mock["followup_questions"],
            "disclaimer": DISCLAIMER,
        }, ensure_ascii=False),
    }


async def _stream_live(initial_state: dict) -> AsyncGenerator[dict, None]:
    from ..agents.graph import debate_graph
    try:
        async for event in debate_graph.astream_events(initial_state, version="v2"):
            kind = event["event"]
            name = event.get("name", "")

            if kind == "on_chain_start" and name in AGENT_DISPLAY:
                yield {
                    "event": "agent_start",
                    "data": json.dumps({
                        "agent": name,
                        "display_name": AGENT_DISPLAY[name]["name"],
                        "emoji": AGENT_DISPLAY[name]["emoji"],
                        "label": AGENT_DISPLAY[name]["label"],
                    }, ensure_ascii=False),
                }
            elif kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    tags = event.get("tags", [])
                    agent = next((t for t in tags if t in AGENT_DISPLAY), None)
                    if agent:
                        yield {
                            "event": "agent_token",
                            "data": json.dumps({"agent": agent, "token": chunk.content}, ensure_ascii=False),
                        }
            elif kind == "on_chain_end" and name in AGENT_DISPLAY:
                output = event.get("data", {}).get("output", {})
                opinion = output.get(f"{name}_opinion", {})
                yield {
                    "event": "agent_done",
                    "data": json.dumps({
                        "agent": name,
                        "opinion": opinion.get("opinion", ""),
                        "confidence": opinion.get("confidence", 0.5),
                    }, ensure_ascii=False),
                }

        final_state = await debate_graph.ainvoke(initial_state)
        yield {
            "event": "debate_complete",
            "data": json.dumps({
                "followup_questions": final_state.get("followup_questions", []),
                "disclaimer": DISCLAIMER,
            }, ensure_ascii=False),
        }
    except Exception as e:
        logger.error(f"Debate streaming error: {e}", exc_info=True)
        yield {"event": "error", "data": json.dumps({"error": str(e)}, ensure_ascii=False)}


@router.post("/start")
async def start_debate(request: DebateRequest):
    bundle = build_evidence_bundle(request.politician_id)
    if bundle.politician_name == "알 수 없음":
        raise HTTPException(status_code=404, detail="의원을 찾을 수 없습니다")
    bundle_dict = bundle.model_dump()

    if _use_mock():
        return EventSourceResponse(_stream_mock(bundle_dict, request.topic or "전체 분석"))

    initial_state = {
        "evidence": bundle_dict,
        "topic": request.topic or "전체 분석",
        "user_question": None,
        "analysis_focus": "",
        "suspicion_opinion": None,
        "optimist_opinion": None,
        "factcheck_opinion": None,
        "followup_questions": [],
        "debate_summary": None,
    }
    return EventSourceResponse(_stream_live(initial_state))


@router.post("/followup")
async def followup_debate(request: FollowupRequest):
    bundle = build_evidence_bundle(request.politician_id)
    if bundle.politician_name == "알 수 없음":
        raise HTTPException(status_code=404, detail="의원을 찾을 수 없습니다")
    bundle_dict = bundle.model_dump()

    if _use_mock():
        return EventSourceResponse(_stream_mock(bundle_dict, "추가 질문", request.question))

    initial_state = {
        "evidence": bundle_dict,
        "topic": "추가 질문",
        "user_question": request.question,
        "analysis_focus": "",
        "suspicion_opinion": None,
        "optimist_opinion": None,
        "factcheck_opinion": None,
        "followup_questions": [],
        "debate_summary": None,
    }
    return EventSourceResponse(_stream_live(initial_state))


@router.post("/sync", response_model=DebateResult)
async def sync_debate(request: DebateRequest):
    bundle = build_evidence_bundle(request.politician_id)
    if bundle.politician_name == "알 수 없음":
        raise HTTPException(status_code=404, detail="의원을 찾을 수 없습니다")
    bundle_dict = bundle.model_dump()
    mock = _build_mock_opinions(bundle_dict, request.topic or "전체 분석")

    opinions = []
    for key, display in AGENT_DISPLAY.items():
        opinions.append(AgentOpinion(
            agent_name=key,
            display_name=display["name"],
            emoji=display["emoji"],
            opinion=mock[key]["opinion"],
            confidence=mock[key]["confidence"],
        ))
    return DebateResult(opinions=opinions, followup_questions=mock["followup_questions"])
