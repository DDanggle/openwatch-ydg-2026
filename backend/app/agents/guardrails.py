"""Post-processing guardrails for agent outputs."""

BANNED_TERMS: dict[str, str] = {
    "의심된다": "시그널이 있다",
    "의심이": "주목할 점이",
    "비리": "추가 확인이 필요한 부분",
    "숨겼다": "신고 내역에서 확인되지 않는",
    "실제 시세": "최근 거래 기반 추정치",
    "확실히": "가능성이 있는",
    "분명히": "데이터상으로",
    "부정축재": "추가 검토가 필요한 자산 증가",
    "탈세": "세무적 검토가 필요한 부분",
    "횡령": "자금 흐름 확인이 필요한 부분",
    "범죄": "법적 검토가 필요한 사안",
}

DISCLAIMER = (
    "⚖️ 이 해석은 공개 신고자료와 실거래 데이터를 바탕으로 한 추정입니다. "
    "법률적 판단이나 사실 확정은 아닙니다."
)


def apply_guardrails(text: str, persona: str) -> str:
    """Apply expression guardrails to agent output."""
    # Replace banned terms
    for banned, replacement in BANNED_TERMS.items():
        text = text.replace(banned, replacement)

    # Ensure fact checker always has disclaimer
    if persona == "factcheck" and DISCLAIMER not in text:
        text += f"\n\n> {DISCLAIMER}"

    return text
