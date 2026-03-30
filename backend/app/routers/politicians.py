"""Politician detail API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..database import get_db
from ..models.schemas import PoliticianDetail, RealEstateGapCard, TimelinePoint

router = APIRouter(prefix="/api/politicians", tags=["politicians"])


@router.get("/{politician_id}", response_model=PoliticianDetail)
def get_politician_detail(politician_id: str):
    """의원 상세 정보 + 자산 요약."""
    with get_db() as conn:
        pol = conn.execute(
            "SELECT * FROM politician_master WHERE id = ?",
            (politician_id,),
        ).fetchone()

        if not pol:
            raise HTTPException(status_code=404, detail="의원을 찾을 수 없습니다")

        # Timeline
        yearly = conn.execute(
            """
            SELECT * FROM asset_disclosure_yearly
            WHERE politician_id = ?
            ORDER BY disclosure_year
            """,
            (politician_id,),
        ).fetchall()

        # Real estate gaps
        gaps = conn.execute(
            """
            SELECT m.*, a.detail
            FROM real_estate_match m
            JOIN asset_itemized a ON m.asset_item_id = a.id
            WHERE m.politician_id = ?
              AND m.match_confidence >= 0.5
            ORDER BY m.gap_pct DESC
            LIMIT 10
            """,
            (politician_id,),
        ).fetchall()

        # Metrics
        metrics = conn.execute(
            """
            SELECT * FROM derived_metrics
            WHERE politician_id = ?
            ORDER BY analysis_end_year DESC
            LIMIT 1
            """,
            (politician_id,),
        ).fetchone()

    timeline = [
        TimelinePoint(
            year=y["disclosure_year"],
            total_assets=y["total_assets"],
            net_assets=y["net_assets"],
            real_estate=y["real_estate_total"],
            deposit=y["deposit_total"],
            securities=y["securities_total"],
            self_amount=y["self_total"],
            spouse_amount=y["spouse_total"],
            family_amount=y["family_total"],
        )
        for y in yearly
    ]

    real_estate_gaps = [
        RealEstateGapCard(
            property_description=g["detail"] or "",
            declared_value=g["declared_valuation"],
            estimated_market_value=g["estimated_market_value"],
            gap_amount=g["gap_amount"],
            gap_pct=g["gap_pct"],
            match_confidence=g["match_confidence"],
            match_method=g["match_method"],
        )
        for g in gaps
    ]

    return PoliticianDetail(
        id=pol["id"],
        name=pol["name"],
        party=pol["party"],
        constituency=pol["constituency"],
        latest_elected=pol["latest_elected"],
        timeline=timeline,
        real_estate_gaps=real_estate_gaps,
        growth_rate=metrics["growth_rate"] if metrics else None,
        cagr=metrics["cagr"] if metrics else None,
        family_contribution_ratio=(
            metrics["family_contribution_ratio"] if metrics else None
        ),
        anomaly_score=metrics["anomaly_score"] if metrics else None,
    )


@router.get("/{politician_id}/assets/timeline")
def get_asset_timeline(
    politician_id: str,
    category: str = Query(None, description="자산 유형 필터"),
    relation: str = Query(None, description="소유 관계 필터"),
):
    """연도별 자산 추이 (차트용 상세 데이터)."""
    with get_db() as conn:
        pol = conn.execute(
            "SELECT id FROM politician_master WHERE id = ?",
            (politician_id,),
        ).fetchone()
        if not pol:
            raise HTTPException(status_code=404, detail="의원을 찾을 수 없습니다")

        # Build query with optional filters
        query = """
            SELECT disclosure_year,
                   asset_type,
                   relation,
                   SUM(current_valuation) as total_value
            FROM asset_itemized
            WHERE politician_id = ?
        """
        params: list = [politician_id]

        if category:
            query += " AND asset_type = ?"
            params.append(category)
        if relation:
            query += " AND relation = ?"
            params.append(relation)

        query += " GROUP BY disclosure_year, asset_type, relation"
        query += " ORDER BY disclosure_year"

        rows = conn.execute(query, params).fetchall()

    return [
        {
            "year": r["disclosure_year"],
            "asset_type": r["asset_type"],
            "relation": r["relation"],
            "total_value": r["total_value"],
        }
        for r in rows
    ]
