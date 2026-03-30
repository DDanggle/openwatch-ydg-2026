"""Ranking API endpoints."""

import json

from fastapi import APIRouter, Query

from ..database import get_db
from ..models.schemas import RankingResponse
from ..services.ranking_service import (
    get_family_contribution_ranking,
    get_growth_ranking,
    get_real_estate_gap_ranking,
)

router = APIRouter(prefix="/api/rankings", tags=["rankings"])


def _get_family_total(conn, politician_name: str, detail: str, area: float) -> dict | None:
    """같은 아파트를 가족이 나눠 소유한 경우 합산 정보 리턴."""
    # 아파트명/동 추출 (간단히 주소 앞 30자 공통)
    if not detail or len(detail) < 20:
        return None
    # 같은 의원의 같은 아파트 (비슷한 주소) 항목 찾기
    addr_prefix = detail[:30]  # 주소 앞부분으로 매칭
    rows = conn.execute("""
        SELECT ai.relation, ai.current_valuation, ai.detail
        FROM asset_itemized ai
        JOIN politician_master pm ON ai.politician_id = pm.id
        WHERE pm.name = ? AND ai.disclosure_year = 2026
          AND ai.asset_type = '건물' AND ai.kind LIKE '%아파트%'
          AND ai.kind NOT LIKE '%전세%'
          AND ai.detail LIKE ?
    """, (politician_name, addr_prefix + "%")).fetchall()

    if len(rows) <= 1:
        return None

    members = [{"relation": r["relation"], "declared": r["current_valuation"]} for r in rows]
    total = sum(r["current_valuation"] for r in rows)
    return {"members": members, "total_declared": total}


def _build_gap_item(r) -> dict:
    meta = {}
    if r["raw_trade_json"]:
        try:
            meta = json.loads(r["raw_trade_json"])
        except (json.JSONDecodeError, TypeError):
            pass
    return {
        "id": r["id"],
        "politician_name": r["politician_name"],
        "politician_position": r["politician_position"],
        "apartment_name": r["apartment_name"],
        "location": f"{r['sido'] or ''} {r['sigungu'] or ''} {r['dong'] or ''}".strip(),
        "area_sqm": r["area_sqm"],
        "declared_value": r["declared_valuation"],
        "estimated_value": r["estimated_market_value"],
        "gap_amount": r["gap_amount"],
        "gap_pct": r["gap_pct"],
        "match_confidence": r["match_confidence"],
        "match_method": r["match_method"],
        "sido": r["sido"],
        "trade_date": meta.get("trade_date"),
        "share_ratio": meta.get("share_ratio"),
        "source": "수동검색(API평균가)" if r["match_method"] == "manual_api_search" else "공공데이터(국토부실거래가)",
        "note": meta.get("note"),
    }


@router.get("/growth", response_model=RankingResponse)
def growth_ranking(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """성장률 랭킹 - CAGR 기준 정렬."""
    return get_growth_ranking(limit=limit, offset=offset)


@router.get("/family-contribution", response_model=RankingResponse)
def family_contribution_ranking(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """가족 재산 기여도 랭킹."""
    return get_family_contribution_ranking(limit=limit, offset=offset)


@router.get("/real-estate-gap", response_model=RankingResponse)
def real_estate_gap_ranking(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """부동산 괴리 랭킹 - 신고가 vs 추정 실거래가 차이."""
    return get_real_estate_gap_ranking(limit=limit, offset=offset)


@router.get("/gap/list")
def gap_detail_list(
    sido: str = Query(None, description="시도 필터 (서울, 경기 등)"),
    sort: str = Query("gap_pct", description="정렬 기준: gap_pct, declared, estimated, name"),
    order: str = Query("desc", description="정렬 방향: asc, desc"),
    limit: int = Query(50, ge=1, le=200),
    min_confidence: float = Query(0.5, ge=0, le=1),
):
    """부동산 괴리 상세 리스트 — 아파트별 신고가 vs 실거래가."""
    with get_db() as conn:
        # Summary stats
        summary_row = conn.execute("""
            SELECT
                COUNT(DISTINCT rm.politician_id) as total_politicians,
                COUNT(*) as total_matches,
                AVG(rm.gap_pct) as avg_gap_pct,
                MAX(rm.gap_pct) as max_gap_pct
            FROM real_estate_match rm
            WHERE rm.match_confidence >= ?
        """, (min_confidence,)).fetchone()

        # Build query
        where_clauses = ["rm.match_confidence >= ?"]
        params: list = [min_confidence]

        if sido:
            where_clauses.append("rm.sido = ?")
            params.append(sido)

        sort_col = {
            "gap_pct": "rm.gap_pct",
            "declared": "rm.declared_valuation",
            "estimated": "rm.estimated_market_value",
            "name": "pm.name",
        }.get(sort, "rm.gap_pct")

        order_dir = "ASC" if order == "asc" else "DESC"

        params.append(limit)

        rows = conn.execute(f"""
            SELECT
                rm.id,
                pm.name as politician_name,
                pm.position as politician_position,
                rm.apartment_name,
                rm.sido,
                rm.sigungu,
                rm.dong,
                rm.area_sqm,
                rm.declared_valuation,
                rm.estimated_market_value,
                rm.gap_amount,
                rm.gap_pct,
                rm.match_confidence,
                rm.match_method,
                rm.raw_trade_json
            FROM real_estate_match rm
            JOIN politician_master pm ON rm.politician_id = pm.id
            WHERE {' AND '.join(where_clauses)}
            ORDER BY {sort_col} {order_dir}
            LIMIT ?
        """, params).fetchall()

        # 시도 목록 (필터용)
        sidos = conn.execute("""
            SELECT DISTINCT sido FROM real_estate_match
            WHERE sido IS NOT NULL AND match_confidence >= ?
            ORDER BY sido
        """, (min_confidence,)).fetchall()

    return {
        "summary": {
            "total_politicians": summary_row["total_politicians"],
            "total_matches": summary_row["total_matches"],
            "avg_gap_pct": round(summary_row["avg_gap_pct"] or 0, 1),
            "max_gap_pct": round(summary_row["max_gap_pct"] or 0, 1),
        },
        "sidos": [r["sido"] for r in sidos],
        "items": [
            _build_gap_item(r)
            for r in rows
        ],
    }


@router.get("/gap/distribution")
def gap_distribution():
    """분포 차트용: 전체 점 데이터 + 예상 구간 + 시도별 요약."""
    with get_db() as conn:
        # 개별 점 데이터
        dots = conn.execute("""
            SELECT rm.id, pm.name as politician_name, pm.party,
                rm.apartment_name,
                rm.sido, rm.sigungu, rm.dong, rm.area_sqm,
                rm.declared_valuation, rm.estimated_market_value,
                rm.gap_pct, rm.match_method, rm.match_confidence,
                rm.raw_trade_json,
                ai.detail as original_detail, ai.relation
            FROM real_estate_match rm
            JOIN politician_master pm ON rm.politician_id = pm.id
            JOIN asset_itemized ai ON rm.asset_item_id = ai.id
            ORDER BY rm.gap_pct
        """).fetchall()

        # 통계
        stats = conn.execute("""
            SELECT COUNT(*) as total,
                AVG(gap_pct) as mean,
                (SELECT gap_pct FROM real_estate_match ORDER BY gap_pct
                 LIMIT 1 OFFSET (SELECT COUNT(*)/2 FROM real_estate_match)) as median,
                (SELECT gap_pct FROM real_estate_match ORDER BY gap_pct
                 LIMIT 1 OFFSET (SELECT COUNT(*)/4 FROM real_estate_match)) as q1,
                (SELECT gap_pct FROM real_estate_match ORDER BY gap_pct
                 LIMIT 1 OFFSET (SELECT COUNT(*)*3/4 FROM real_estate_match)) as q3
            FROM real_estate_match
        """).fetchone()

        # 예상 구간 초과 건수 (공시가 현실화율 ~69% 기준 = 약 +45% 괴리가 제도적 범위)
        expected_upper = 70  # +70% 이상은 초과 괴리
        excess = conn.execute(
            "SELECT COUNT(*) as c FROM real_estate_match WHERE gap_pct > ?", (expected_upper,)
        ).fetchone()["c"]
        high_conf = conn.execute(
            "SELECT COUNT(*) as c FROM real_estate_match WHERE match_confidence >= 0.7"
        ).fetchone()["c"]

        # 시도별 요약
        regions = conn.execute("""
            SELECT sido, COUNT(*) as count,
                AVG(gap_pct) as avg_gap,
                MIN(gap_pct) as min_gap, MAX(gap_pct) as max_gap,
                SUM(CASE WHEN gap_pct > 70 THEN 1 ELSE 0 END) as excess_count
            FROM real_estate_match WHERE sido IS NOT NULL
            GROUP BY sido ORDER BY AVG(gap_pct) DESC
        """).fetchall()

        # 의원별 포트폴리오
        portfolios = conn.execute("""
            SELECT pm.name, pm.position, pm.party, rm.politician_id,
                COUNT(*) as asset_count,
                SUM(rm.declared_valuation) as total_declared,
                SUM(rm.estimated_market_value) as total_estimated,
                AVG(rm.gap_pct) as avg_gap,
                MAX(rm.gap_pct) as max_gap,
                GROUP_CONCAT(rm.apartment_name, ', ') as apartments,
                GROUP_CONCAT(DISTINCT rm.sido) as sidos
            FROM real_estate_match rm
            JOIN politician_master pm ON rm.politician_id = pm.id
            GROUP BY rm.politician_id
            ORDER BY pm.name
        """).fetchall()

        # Build dots inside connection context
        built_dots = []
        for d in dots:
            meta = {}
            if d["raw_trade_json"]:
                try: meta = json.loads(d["raw_trade_json"])
                except: pass
            built_dots.append({
                "id": d["id"],
                "name": d["politician_name"],
                "party": d["party"],
                "apt": d["apartment_name"],
                "sido": d["sido"],
                "sigungu": d["sigungu"],
                "dong": d["dong"],
                "area": d["area_sqm"],
                "declared": d["declared_valuation"],
                "estimated": d["estimated_market_value"],
                "gap": round(d["gap_pct"], 1),
                "method": d["match_method"],
                "confidence": d["match_confidence"],
                "detail": d["original_detail"],
                "relation": d["relation"],
                "trade_date": meta.get("trade_date", ""),
                "share_ratio": meta.get("share_ratio", 1),
                "family_total": _get_family_total(conn, d["politician_name"], d["original_detail"], d["area_sqm"]),
            })

    return {
        "stats": {
            "total": stats["total"],
            "mean": round(stats["mean"] or 0, 1),
            "median": round(stats["median"] or 0, 1),
            "q1": round(stats["q1"] or 0, 1),
            "q3": round(stats["q3"] or 0, 1),
            "expected_band": [25, expected_upper],
            "excess_count": excess,
            "high_confidence_count": high_conf,
            "high_confidence_pct": round(high_conf / stats["total"] * 100, 0) if stats["total"] else 0,
        },
        "dots": built_dots,
        "regions": [
            {
                "sido": r["sido"],
                "count": r["count"],
                "avg_gap": round(r["avg_gap"], 1),
                "min_gap": round(r["min_gap"], 1),
                "max_gap": round(r["max_gap"], 1),
                "excess_count": r["excess_count"],
            }
            for r in regions
        ],
        "portfolios": [
            {
                "name": p["name"],
                "position": p["position"],
                "party": p["party"],
                "politician_id": p["politician_id"],
                "asset_count": p["asset_count"],
                "total_declared": p["total_declared"],
                "total_estimated": p["total_estimated"],
                "avg_gap": round(p["avg_gap"], 1),
                "max_gap": round(p["max_gap"], 1),
                "apartments": p["apartments"],
                "sidos": p["sidos"],
            }
            for p in portfolios
        ],
    }


@router.get("/gap/unmatched")
def gap_unmatched_list():
    """미매칭 아파트 리스트 — 아직 실거래가 비교 안 된 항목."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT
                pm.name as politician_name,
                pm.position as politician_position,
                ai.kind,
                ai.current_valuation,
                ai.detail,
                ai.relation
            FROM asset_itemized ai
            JOIN politician_master pm ON ai.politician_id = pm.id
            WHERE ai.disclosure_year = 2026
              AND ai.asset_type = '건물'
              AND ai.kind LIKE '%아파트%'
              AND ai.kind NOT LIKE '%전세%'
              AND ai.kind NOT LIKE '%임차%'
              AND ai.politician_id NOT IN (
                  SELECT DISTINCT politician_id FROM real_estate_match
              )
            ORDER BY ai.current_valuation DESC
        """).fetchall()

    return {
        "total": len(rows),
        "items": [
            {
                "politician_name": r["politician_name"],
                "politician_position": r["politician_position"],
                "kind": r["kind"],
                "declared_value": r["current_valuation"],
                "detail": r["detail"],
                "relation": r["relation"],
            }
            for r in rows
        ],
    }
