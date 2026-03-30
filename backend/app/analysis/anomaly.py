"""Anomaly detection: sudden spikes, debt vanish, family transfers, etc."""

from __future__ import annotations

import statistics

from ..database import get_db

# 국회의원 선거 연도
ELECTION_YEARS = {17: 2004, 18: 2008, 19: 2012, 20: 2016, 21: 2020, 22: 2024}


def anomaly_detector(politician_id: str) -> dict:
    """
    Detect anomalous patterns in a politician's asset history.

    Returns:
        flags: dict of boolean anomaly flags
        anomaly_score: composite score 0-100
        details: dict of details for each triggered flag
    """
    flags: dict[str, bool] = {
        "sudden_spike": False,
        "debt_vanish": False,
        "family_transfer": False,
        "election_year_pattern": False,
        "asset_shuffle": False,
    }
    details: dict[str, str] = {}
    score = 0.0

    with get_db() as conn:
        yearly = conn.execute(
            """
            SELECT * FROM asset_disclosure_yearly
            WHERE politician_id = ?
            ORDER BY disclosure_year
            """,
            (politician_id,),
        ).fetchall()

        # Get all politicians' YoY changes for z-score calculation
        all_yoy = conn.execute(
            """
            SELECT yoy_change FROM asset_disclosure_yearly
            WHERE yoy_change != 0
            """
        ).fetchall()

    if len(yearly) < 2:
        return {"flags": flags, "anomaly_score": 0.0, "details": details}

    # Compute z-score baseline
    all_changes = [r["yoy_change"] for r in all_yoy if r["yoy_change"]]
    if len(all_changes) > 2:
        median_change = statistics.median(all_changes)
        stdev_change = statistics.stdev(all_changes)
    else:
        median_change = 0
        stdev_change = 1

    for i in range(1, len(yearly)):
        cur = yearly[i]
        prev = yearly[i - 1]
        year = cur["disclosure_year"]

        # ── 1. Sudden spike ──
        if stdev_change > 0:
            z = abs(cur["yoy_change"] - median_change) / stdev_change
            if z > 2.5:
                flags["sudden_spike"] = True
                details["sudden_spike"] = (
                    f"{year}년 자산 변동 {cur['yoy_change']:,}원 "
                    f"(z-score: {z:.1f})"
                )
                score += min(20 + (z - 2.5) * 5, 30)

        # ── 2. Debt vanish ──
        if prev["total_debt"] > 0:
            debt_change_pct = (
                (prev["total_debt"] - cur["total_debt"]) / prev["total_debt"] * 100
            )
            if debt_change_pct > 50:
                flags["debt_vanish"] = True
                details["debt_vanish"] = (
                    f"{year}년 채무 {debt_change_pct:.0f}% 감소 "
                    f"({prev['total_debt']:,} → {cur['total_debt']:,})"
                )
                score += 20

        # ── 3. Family transfer ──
        self_delta = cur["self_total"] - prev["self_total"]
        family_delta = cur["family_total"] - prev["family_total"]

        # Family up while self down (or vice versa)
        if (self_delta < 0 and family_delta > 0) or (
            self_delta > 0 and family_delta < 0
        ):
            magnitude = min(abs(self_delta), abs(family_delta))
            if magnitude > abs(cur["net_assets"]) * 0.1:  # > 10% of net assets
                flags["family_transfer"] = True
                details["family_transfer"] = (
                    f"{year}년 본인 {self_delta:+,}원, "
                    f"가족 {family_delta:+,}원 (역방향 이동)"
                )
                score += 20

        # ── 4. Election year pattern ──
        election_years = set(ELECTION_YEARS.values())
        if year in election_years or year - 1 in election_years:
            if abs(cur["yoy_change"]) > abs(prev.get("yoy_change", 0) or 0) * 2:
                flags["election_year_pattern"] = True
                details["election_year_pattern"] = (
                    f"{year}년(선거 전후) 변동폭이 전년 대비 2배 이상"
                )
                score += 15

    # Cap score at 100
    score = min(score, 100.0)

    return {
        "flags": flags,
        "anomaly_score": round(score, 1),
        "details": details,
    }
