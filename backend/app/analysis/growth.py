"""Growth score calculation: CAGR, absolute growth, growth rate."""

from __future__ import annotations

import json
import logging
import math

from ..database import get_db

logger = logging.getLogger(__name__)

MAX_GROWTH_RATE = 9999.0  # Cap for start=0 edge case


def growth_score(
    politician_id: str,
    start_year: int | None = None,
    end_year: int | None = None,
) -> dict:
    """
    Calculate growth metrics for a single politician.

    Returns dict with: cagr, absolute_growth, growth_rate
    """
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT disclosure_year, net_assets
            FROM asset_disclosure_yearly
            WHERE politician_id = ?
            ORDER BY disclosure_year
            """,
            (politician_id,),
        ).fetchall()

    if len(rows) < 2:
        return {"cagr": None, "absolute_growth": 0, "growth_rate": 0.0}

    if start_year:
        rows = [r for r in rows if r["disclosure_year"] >= start_year]
    if end_year:
        rows = [r for r in rows if r["disclosure_year"] <= end_year]

    if len(rows) < 2:
        return {"cagr": None, "absolute_growth": 0, "growth_rate": 0.0}

    start_net = rows[0]["net_assets"]
    end_net = rows[-1]["net_assets"]
    years = rows[-1]["disclosure_year"] - rows[0]["disclosure_year"]

    absolute_growth = end_net - start_net

    # Growth rate
    if start_net == 0:
        growth_rate = MAX_GROWTH_RATE if end_net > 0 else 0.0
    else:
        growth_rate = min(absolute_growth / abs(start_net) * 100, MAX_GROWTH_RATE)

    # CAGR
    cagr = None
    if years > 0 and start_net > 0 and end_net > 0:
        try:
            cagr = (math.pow(end_net / start_net, 1 / years) - 1) * 100
        except (ValueError, ZeroDivisionError, OverflowError):
            cagr = None

    return {
        "cagr": cagr,
        "absolute_growth": absolute_growth,
        "growth_rate": growth_rate,
        "start_year": rows[0]["disclosure_year"],
        "end_year": rows[-1]["disclosure_year"],
        "start_net": start_net,
        "end_net": end_net,
    }


def compute_all_growth_metrics() -> int:
    """Compute growth metrics for all politicians and store in derived_metrics."""
    logger.info("Computing growth metrics for all politicians...")

    with get_db() as conn:
        politicians = conn.execute(
            "SELECT DISTINCT politician_id FROM asset_disclosure_yearly"
        ).fetchall()

    count = 0
    with get_db() as conn:
        for row in politicians:
            pid = row["politician_id"]
            metrics = growth_score(pid)

            if metrics["cagr"] is None and metrics["absolute_growth"] == 0:
                continue

            # Also compute family metrics
            from .family import family_contribution_score

            family = family_contribution_score(pid)

            # Also compute anomaly
            from .anomaly import anomaly_detector

            anomaly = anomaly_detector(pid)

            conn.execute(
                """
                INSERT INTO derived_metrics (
                    politician_id, analysis_start_year, analysis_end_year,
                    cagr, absolute_growth, growth_rate,
                    family_contribution_ratio, spouse_contribution_ratio,
                    family_growth_share,
                    anomaly_flags, anomaly_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(politician_id, analysis_start_year, analysis_end_year)
                DO UPDATE SET
                    cagr=excluded.cagr,
                    absolute_growth=excluded.absolute_growth,
                    growth_rate=excluded.growth_rate,
                    family_contribution_ratio=excluded.family_contribution_ratio,
                    spouse_contribution_ratio=excluded.spouse_contribution_ratio,
                    family_growth_share=excluded.family_growth_share,
                    anomaly_flags=excluded.anomaly_flags,
                    anomaly_score=excluded.anomaly_score,
                    computed_at=datetime('now')
                """,
                (
                    pid,
                    metrics.get("start_year", 0),
                    metrics.get("end_year", 0),
                    metrics["cagr"],
                    metrics["absolute_growth"],
                    metrics["growth_rate"],
                    family.get("family_contribution_ratio", 0),
                    family.get("spouse_contribution_ratio", 0),
                    family.get("family_growth_share", 0),
                    json.dumps(anomaly.get("flags", {}), ensure_ascii=False),
                    anomaly.get("anomaly_score", 0),
                ),
            )
            count += 1

    logger.info(f"Computed metrics for {count} politicians")
    return count
