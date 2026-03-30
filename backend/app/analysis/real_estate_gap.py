"""Real estate gap score: 신고가 vs 실거래 추정치."""

from __future__ import annotations

from ..database import get_db


def real_estate_gap_score(politician_id: str) -> dict:
    """
    Calculate real estate valuation gap metrics.

    Returns:
        avg_gap_pct: average gap percentage across matched properties
        max_gap_pct: maximum single gap
        weighted_gap: gap weighted by declared value
        matched_count: number of matched properties
        total_count: total real estate items
        undervalued: list of items with gap > 30%
    """
    with get_db() as conn:
        matches = conn.execute(
            """
            SELECT m.*, a.detail, a.disclosure_year
            FROM real_estate_match m
            JOIN asset_itemized a ON m.asset_item_id = a.id
            WHERE m.politician_id = ?
              AND m.match_confidence >= 0.5
            ORDER BY m.gap_pct DESC
            """,
            (politician_id,),
        ).fetchall()

        total_count = conn.execute(
            """
            SELECT COUNT(*) as c FROM asset_itemized
            WHERE politician_id = ?
              AND asset_type IN ('건물', '부동산')
            """,
            (politician_id,),
        ).fetchone()["c"]

    if not matches:
        return {
            "avg_gap_pct": None,
            "max_gap_pct": None,
            "weighted_gap": None,
            "matched_count": 0,
            "total_count": total_count,
            "undervalued": [],
        }

    gaps = [m["gap_pct"] for m in matches]
    avg_gap = sum(gaps) / len(gaps)
    max_gap = max(gaps)

    # Weighted gap (bigger properties matter more)
    total_declared = sum(m["declared_valuation"] for m in matches)
    if total_declared > 0:
        weighted_gap = sum(
            m["gap_pct"] * m["declared_valuation"] / total_declared
            for m in matches
        )
    else:
        weighted_gap = avg_gap

    undervalued = [
        {
            "detail": m["detail"],
            "declared": m["declared_valuation"],
            "estimated": m["estimated_market_value"],
            "gap_pct": m["gap_pct"],
            "confidence": m["match_confidence"],
            "year": m["disclosure_year"],
        }
        for m in matches
        if m["gap_pct"] > 30
    ]

    return {
        "avg_gap_pct": round(avg_gap, 2),
        "max_gap_pct": round(max_gap, 2),
        "weighted_gap": round(weighted_gap, 2),
        "matched_count": len(matches),
        "total_count": total_count,
        "undervalued": undervalued,
    }
