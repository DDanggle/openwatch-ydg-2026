"""Ranking computation service."""

from __future__ import annotations

from ..database import get_db
from ..models.schemas import RankedPolitician, RankingResponse


def get_growth_ranking(limit: int = 20, offset: int = 0) -> RankingResponse:
    """Get politicians ranked by asset growth rate (CAGR)."""
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT
                dm.politician_id,
                pm.name,
                pm.party,
                pm.constituency,
                dm.cagr,
                dm.absolute_growth,
                dm.growth_rate,
                (SELECT net_assets FROM asset_disclosure_yearly
                 WHERE politician_id = dm.politician_id
                 ORDER BY disclosure_year DESC LIMIT 1) as latest_net
            FROM derived_metrics dm
            JOIN politician_master pm ON dm.politician_id = pm.id
            WHERE dm.cagr IS NOT NULL
            ORDER BY dm.cagr DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()

        total = conn.execute(
            "SELECT COUNT(*) as c FROM derived_metrics WHERE cagr IS NOT NULL"
        ).fetchone()["c"]

    items = [
        RankedPolitician(
            rank=offset + i + 1,
            politician_id=r["politician_id"],
            name=r["name"],
            party=r["party"],
            constituency=r["constituency"],
            metric_value=round(r["cagr"], 2),
            metric_label="CAGR (%)",
            total_assets_current=r["latest_net"] or 0,
        )
        for i, r in enumerate(rows)
    ]

    return RankingResponse(
        ranking_type="growth",
        total_count=total,
        items=items,
    )


def get_family_contribution_ranking(
    limit: int = 20, offset: int = 0
) -> RankingResponse:
    """Get politicians ranked by family asset contribution ratio."""
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT
                dm.politician_id,
                pm.name,
                pm.party,
                pm.constituency,
                dm.family_contribution_ratio,
                (SELECT net_assets FROM asset_disclosure_yearly
                 WHERE politician_id = dm.politician_id
                 ORDER BY disclosure_year DESC LIMIT 1) as latest_net
            FROM derived_metrics dm
            JOIN politician_master pm ON dm.politician_id = pm.id
            WHERE dm.family_contribution_ratio > 0
            ORDER BY dm.family_contribution_ratio DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()

        total = conn.execute(
            "SELECT COUNT(*) as c FROM derived_metrics "
            "WHERE family_contribution_ratio > 0"
        ).fetchone()["c"]

    items = [
        RankedPolitician(
            rank=offset + i + 1,
            politician_id=r["politician_id"],
            name=r["name"],
            party=r["party"],
            constituency=r["constituency"],
            metric_value=round(r["family_contribution_ratio"] * 100, 2),
            metric_label="가족 기여도 (%)",
            total_assets_current=r["latest_net"] or 0,
        )
        for i, r in enumerate(rows)
    ]

    return RankingResponse(
        ranking_type="family-contribution",
        total_count=total,
        items=items,
    )


def get_real_estate_gap_ranking(
    limit: int = 20, offset: int = 0
) -> RankingResponse:
    """Get politicians ranked by real estate valuation gap."""
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT
                dm.politician_id,
                pm.name,
                pm.party,
                pm.constituency,
                dm.avg_gap_pct,
                (SELECT net_assets FROM asset_disclosure_yearly
                 WHERE politician_id = dm.politician_id
                 ORDER BY disclosure_year DESC LIMIT 1) as latest_net
            FROM derived_metrics dm
            JOIN politician_master pm ON dm.politician_id = pm.id
            WHERE dm.avg_gap_pct IS NOT NULL AND dm.avg_gap_pct > 0
            ORDER BY dm.avg_gap_pct DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()

        total = conn.execute(
            "SELECT COUNT(*) as c FROM derived_metrics "
            "WHERE avg_gap_pct IS NOT NULL AND avg_gap_pct > 0"
        ).fetchone()["c"]

    items = [
        RankedPolitician(
            rank=offset + i + 1,
            politician_id=r["politician_id"],
            name=r["name"],
            party=r["party"],
            constituency=r["constituency"],
            metric_value=round(r["avg_gap_pct"], 2),
            metric_label="괴리율 (%)",
            total_assets_current=r["latest_net"] or 0,
        )
        for i, r in enumerate(rows)
    ]

    return RankingResponse(
        ranking_type="real-estate-gap",
        total_count=total,
        items=items,
    )
