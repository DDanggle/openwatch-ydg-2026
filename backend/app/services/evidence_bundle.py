"""Build evidence bundles for the debate agents."""

from __future__ import annotations

from ..database import get_db
from ..models.schemas import (
    AssetChangeEvent,
    AssetTimelineEntry,
    ComputedMetrics,
    EvidenceBundle,
)


def build_evidence_bundle(politician_id: str) -> EvidenceBundle:
    """Assemble all data needed for agent analysis."""
    with get_db() as conn:
        # Politician info
        pol = conn.execute(
            "SELECT * FROM politician_master WHERE id = ?",
            (politician_id,),
        ).fetchone()

        if not pol:
            return EvidenceBundle(politician_name="알 수 없음")

        # Yearly aggregates
        yearly = conn.execute(
            """
            SELECT * FROM asset_disclosure_yearly
            WHERE politician_id = ?
            ORDER BY disclosure_year
            """,
            (politician_id,),
        ).fetchall()

        # Significant changes (top 10 by absolute change)
        changes = conn.execute(
            """
            SELECT disclosure_year, asset_type, relation, detail,
                   origin_valuation, current_valuation,
                   (current_valuation - origin_valuation) as change_amount
            FROM asset_itemized
            WHERE politician_id = ?
              AND ABS(current_valuation - origin_valuation) > 0
            ORDER BY ABS(current_valuation - origin_valuation) DESC
            LIMIT 10
            """,
            (politician_id,),
        ).fetchall()

        # Derived metrics
        metrics_row = conn.execute(
            """
            SELECT * FROM derived_metrics
            WHERE politician_id = ?
            ORDER BY analysis_end_year DESC
            LIMIT 1
            """,
            (politician_id,),
        ).fetchone()

    # Build timeline
    timeline: list[AssetTimelineEntry] = []
    for y in yearly:
        total = y["total_assets"]
        timeline.append(
            AssetTimelineEntry(
                year=y["disclosure_year"],
                total_amount=total,
                net_amount=y["net_assets"],
                breakdown_by_type={
                    "부동산": y["real_estate_total"],
                    "예금": y["deposit_total"],
                    "증권": y["securities_total"],
                    "기타": max(0, total - y["real_estate_total"]
                                - y["deposit_total"] - y["securities_total"]),
                },
                breakdown_by_family={
                    "본인": y["self_total"],
                    "배우자": y["spouse_total"],
                    "기타가족": max(0, y["family_total"] - y["spouse_total"]),
                },
            )
        )

    # Build significant changes
    sig_changes: list[AssetChangeEvent] = []
    for c in changes:
        prev = c["origin_valuation"]
        cur = c["current_valuation"]
        change = c["change_amount"]
        pct = (change / prev * 100) if prev > 0 else 0.0

        sig_changes.append(
            AssetChangeEvent(
                year=c["disclosure_year"],
                category=c["asset_type"],
                relation=c["relation"],
                description=c["detail"],
                previous_amount=prev,
                current_amount=cur,
                change_amount=change,
                change_pct=round(pct, 2),
            )
        )

    # Build metrics
    import json

    metrics = ComputedMetrics()
    if metrics_row:
        anomaly_flags = {}
        if metrics_row["anomaly_flags"]:
            try:
                anomaly_flags = json.loads(metrics_row["anomaly_flags"])
            except json.JSONDecodeError:
                pass

        # Calculate real_estate_share from latest yearly
        re_share = 0.0
        if yearly:
            latest = yearly[-1]
            total = latest["total_assets"]
            if total > 0:
                re_share = latest["real_estate_total"] / total

        metrics = ComputedMetrics(
            cagr=metrics_row["cagr"],
            absolute_growth=metrics_row["absolute_growth"] or 0,
            growth_rate=metrics_row["growth_rate"] or 0.0,
            family_contribution_ratio=metrics_row["family_contribution_ratio"] or 0.0,
            spouse_contribution_ratio=metrics_row["spouse_contribution_ratio"] or 0.0,
            real_estate_share=re_share,
            avg_gap_pct=metrics_row["avg_gap_pct"],
            anomaly_score=metrics_row["anomaly_score"] or 0.0,
            anomaly_flags=anomaly_flags,
        )

    return EvidenceBundle(
        politician_name=pol["name"],
        party=pol["party"],
        district=pol["constituency"],
        timeline=timeline,
        significant_changes=sig_changes,
        metrics=metrics,
    )
