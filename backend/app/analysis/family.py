"""Family contribution score calculation."""

from __future__ import annotations

from ..database import get_db


def family_contribution_score(politician_id: str) -> dict:
    """
    Calculate family asset contribution metrics.

    Returns:
        family_contribution_ratio: family / (self + family) at latest year
        spouse_contribution_ratio: spouse / total at latest year
        family_growth_share: portion of total growth from family members
        flags: list of notable patterns
    """
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT disclosure_year, net_assets, total_assets,
                   self_total, spouse_total, family_total
            FROM asset_disclosure_yearly
            WHERE politician_id = ?
            ORDER BY disclosure_year
            """,
            (politician_id,),
        ).fetchall()

    if not rows:
        return {
            "family_contribution_ratio": 0.0,
            "spouse_contribution_ratio": 0.0,
            "family_growth_share": 0.0,
            "flags": [],
        }

    latest = rows[-1]
    total = latest["self_total"] + latest["family_total"]

    # Family contribution at latest year
    family_ratio = latest["family_total"] / total if total > 0 else 0.0
    spouse_ratio = latest["spouse_total"] / total if total > 0 else 0.0

    # Family growth share (what portion of growth came from family)
    family_growth_share = 0.0
    flags: list[str] = []

    if len(rows) >= 2:
        first = rows[0]
        delta_total = latest["net_assets"] - first["net_assets"]
        delta_family = latest["family_total"] - first["family_total"]

        if delta_total > 0:
            family_growth_share = max(0, min(1, delta_family / delta_total))

        # Flag: spouse dominant
        if spouse_ratio > 0.6:
            flags.append("spouse_dominant")

        # Flag: family surge (family 3x growth while self flat)
        if first["family_total"] > 0:
            family_growth = latest["family_total"] / first["family_total"]
            self_growth = (
                latest["self_total"] / first["self_total"]
                if first["self_total"] > 0
                else 1.0
            )
            if family_growth > 3.0 and self_growth < 1.5:
                flags.append("family_surge")

    return {
        "family_contribution_ratio": round(family_ratio, 4),
        "spouse_contribution_ratio": round(spouse_ratio, 4),
        "family_growth_share": round(family_growth_share, 4),
        "flags": flags,
    }
