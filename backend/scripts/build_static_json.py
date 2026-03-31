#!/usr/bin/env python3
"""SQLite → JSON 정적 파일 빌드. Vercel 배포용."""

import json
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "wealth_tracker.db"
OUT_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "public" / "data"


def build():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    # ── 1. gap/distribution ──
    dots_raw = conn.execute("""
        SELECT rm.id, pm.name as politician_name, pm.party,
            rm.apartment_name, rm.sido, rm.sigungu, rm.dong, rm.area_sqm,
            rm.declared_valuation, rm.estimated_market_value,
            rm.gap_pct, rm.match_method, rm.match_confidence,
            rm.raw_trade_json, ai.detail as original_detail, ai.relation
        FROM real_estate_match rm
        JOIN politician_master pm ON rm.politician_id = pm.id
        JOIN asset_itemized ai ON rm.asset_item_id = ai.id
        ORDER BY rm.gap_pct
    """).fetchall()

    stats = conn.execute("""
        SELECT COUNT(*) as total, AVG(gap_pct) as mean,
            (SELECT gap_pct FROM real_estate_match ORDER BY gap_pct LIMIT 1 OFFSET (SELECT COUNT(*)/2 FROM real_estate_match)) as median,
            (SELECT gap_pct FROM real_estate_match ORDER BY gap_pct LIMIT 1 OFFSET (SELECT COUNT(*)/4 FROM real_estate_match)) as q1,
            (SELECT gap_pct FROM real_estate_match ORDER BY gap_pct LIMIT 1 OFFSET (SELECT COUNT(*)*3/4 FROM real_estate_match)) as q3
        FROM real_estate_match
    """).fetchone()

    expected_upper = 70
    excess = conn.execute("SELECT COUNT(*) as c FROM real_estate_match WHERE gap_pct > ?", (expected_upper,)).fetchone()["c"]
    high_conf = conn.execute("SELECT COUNT(*) as c FROM real_estate_match WHERE match_confidence >= 0.7").fetchone()["c"]

    regions = conn.execute("""
        SELECT sido, COUNT(*) as count, AVG(gap_pct) as avg_gap,
            MIN(gap_pct) as min_gap, MAX(gap_pct) as max_gap,
            SUM(CASE WHEN gap_pct > 70 THEN 1 ELSE 0 END) as excess_count
        FROM real_estate_match WHERE sido IS NOT NULL GROUP BY sido ORDER BY AVG(gap_pct) DESC
    """).fetchall()

    portfolios = conn.execute("""
        SELECT pm.name, pm.position, pm.party, rm.politician_id,
            COUNT(*) as asset_count,
            SUM(rm.declared_valuation) as total_declared,
            SUM(rm.estimated_market_value) as total_estimated,
            AVG(rm.gap_pct) as avg_gap, MAX(rm.gap_pct) as max_gap,
            GROUP_CONCAT(rm.apartment_name, ', ') as apartments,
            GROUP_CONCAT(DISTINCT rm.sido) as sidos
        FROM real_estate_match rm JOIN politician_master pm ON rm.politician_id = pm.id
        GROUP BY rm.politician_id ORDER BY pm.name
    """).fetchall()

    def get_family(name, detail, area):
        if not detail or len(detail) < 20:
            return None
        rows = conn.execute("""
            SELECT ai.relation, ai.current_valuation FROM asset_itemized ai
            JOIN politician_master pm ON ai.politician_id = pm.id
            WHERE pm.name=? AND ai.disclosure_year=2026 AND ai.asset_type='건물'
            AND ai.kind LIKE '%아파트%' AND ai.kind NOT LIKE '%전세%' AND ai.detail LIKE ?
        """, (name, detail[:30] + "%")).fetchall()
        if len(rows) <= 1:
            return None
        return {"members": [{"relation": r["relation"], "declared": r["current_valuation"]} for r in rows],
                "total_declared": sum(r["current_valuation"] for r in rows)}

    built_dots = []
    for d in dots_raw:
        meta = json.loads(d["raw_trade_json"]) if d["raw_trade_json"] else {}
        built_dots.append({
            "id": d["id"], "name": d["politician_name"], "party": d["party"],
            "apt": d["apartment_name"], "sido": d["sido"], "sigungu": d["sigungu"], "dong": d["dong"],
            "area": d["area_sqm"],
            "declared": d["declared_valuation"], "estimated": d["estimated_market_value"],
            "gap": round(d["gap_pct"], 1), "method": d["match_method"], "confidence": d["match_confidence"],
            "detail": d["original_detail"], "relation": d["relation"],
            "trade_date": meta.get("trade_date", ""), "share_ratio": meta.get("share_ratio", 1),
            "family_total": get_family(d["politician_name"], d["original_detail"], d["area_sqm"]),
        })

    gap_data = {
        "stats": {
            "total": stats["total"], "mean": round(stats["mean"] or 0, 1),
            "median": round(stats["median"] or 0, 1),
            "q1": round(stats["q1"] or 0, 1), "q3": round(stats["q3"] or 0, 1),
            "expected_band": [25, expected_upper], "excess_count": excess,
            "high_confidence_count": high_conf,
            "high_confidence_pct": round(high_conf / stats["total"] * 100, 0) if stats["total"] else 0,
        },
        "dots": built_dots,
        "regions": [{"sido": r["sido"], "count": r["count"], "avg_gap": round(r["avg_gap"], 1),
                     "min_gap": round(r["min_gap"], 1), "max_gap": round(r["max_gap"], 1),
                     "excess_count": r["excess_count"]} for r in regions],
        "portfolios": [{"name": p["name"], "position": p["position"], "party": p["party"],
                        "politician_id": p["politician_id"], "asset_count": p["asset_count"],
                        "total_declared": p["total_declared"], "total_estimated": p["total_estimated"],
                        "avg_gap": round(p["avg_gap"], 1), "max_gap": round(p["max_gap"], 1),
                        "apartments": p["apartments"], "sidos": p["sidos"]} for p in portfolios],
    }

    with open(OUT_DIR / "gap_distribution.json", "w", encoding="utf-8") as f:
        json.dump(gap_data, f, ensure_ascii=False)
    print(f"  gap_distribution.json: {len(built_dots)} dots, {len(regions)} regions")

    # ── 2. rankings ──
    for ranking_type, query, label in [
        ("growth", "SELECT pm.id as pid, pm.name, pm.party, pm.constituency, dm.growth_rate as metric, "
                   "(SELECT net_assets FROM asset_disclosure_yearly WHERE politician_id=pm.id AND disclosure_year=2026) as net "
                   "FROM derived_metrics dm JOIN politician_master pm ON dm.politician_id=pm.id "
                   "WHERE dm.growth_rate > 0 ORDER BY dm.growth_rate DESC LIMIT 50", "CAGR (%)"),
        ("family", "SELECT pm.id as pid, pm.name, pm.party, pm.constituency, dm.family_contribution_ratio*100 as metric, "
                   "(SELECT net_assets FROM asset_disclosure_yearly WHERE politician_id=pm.id AND disclosure_year=2026) as net "
                   "FROM derived_metrics dm JOIN politician_master pm ON dm.politician_id=pm.id "
                   "WHERE dm.family_contribution_ratio > 0 ORDER BY dm.family_contribution_ratio DESC LIMIT 50", "가족 기여도 (%)"),
        ("gap", "SELECT pm.id as pid, pm.name, pm.party, pm.constituency, dm.avg_gap_pct as metric, "
                "(SELECT net_assets FROM asset_disclosure_yearly WHERE politician_id=pm.id AND disclosure_year=2026) as net "
                "FROM derived_metrics dm JOIN politician_master pm ON dm.politician_id=pm.id "
                "WHERE dm.avg_gap_pct IS NOT NULL AND dm.avg_gap_pct > 0 ORDER BY dm.avg_gap_pct DESC LIMIT 50", "괴리율 (%)"),
    ]:
        rows = conn.execute(query).fetchall()
        items = [{
            "rank": i + 1, "politician_id": r["pid"], "name": r["name"],
            "party": r["party"], "constituency": r["constituency"],
            "metric_value": round(r["metric"], 2), "metric_label": label,
            "total_assets_current": r["net"] or 0,
        } for i, r in enumerate(rows)]
        data = {"ranking_type": ranking_type, "total_count": len(items), "items": items}
        with open(OUT_DIR / f"ranking_{ranking_type}.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        print(f"  ranking_{ranking_type}.json: {len(items)} items")

    # ── 3. politician detail (각 의원별) ──
    pols = conn.execute("SELECT id, name, party, position, constituency, latest_elected FROM politician_master").fetchall()
    pol_details = {}
    for p in pols:
        yearly = conn.execute("""
            SELECT * FROM asset_disclosure_yearly WHERE politician_id=? ORDER BY disclosure_year
        """, (p["id"],)).fetchall()
        gaps = conn.execute("""
            SELECT m.*, a.detail FROM real_estate_match m
            JOIN asset_itemized a ON m.asset_item_id = a.id
            WHERE m.politician_id=? AND m.match_confidence >= 0.5
            ORDER BY m.gap_pct DESC LIMIT 10
        """, (p["id"],)).fetchall()
        metrics = conn.execute("SELECT * FROM derived_metrics WHERE politician_id=? LIMIT 1", (p["id"],)).fetchone()

        pol_details[p["id"]] = {
            "id": p["id"], "name": p["name"], "party": p["party"],
            "constituency": p["constituency"], "latest_elected": p["latest_elected"],
            "timeline": [{"year": y["disclosure_year"], "total_assets": y["total_assets"],
                         "net_assets": y["net_assets"], "real_estate": y["real_estate_total"],
                         "deposit": y["deposit_total"], "securities": y["securities_total"],
                         "self_amount": y["self_total"], "spouse_amount": y["spouse_total"],
                         "family_amount": y["family_total"]} for y in yearly],
            "real_estate_gaps": [{"property_description": g["detail"] or "", "declared_value": g["declared_valuation"],
                                 "estimated_market_value": g["estimated_market_value"],
                                 "gap_amount": g["gap_amount"], "gap_pct": g["gap_pct"],
                                 "match_confidence": g["match_confidence"], "match_method": g["match_method"]}
                                for g in gaps],
            "growth_rate": metrics["growth_rate"] if metrics else None,
            "cagr": metrics["cagr"] if metrics else None,
            "family_contribution_ratio": metrics["family_contribution_ratio"] if metrics else None,
            "anomaly_score": metrics["anomaly_score"] if metrics else None,
        }

    with open(OUT_DIR / "politicians.json", "w", encoding="utf-8") as f:
        json.dump(pol_details, f, ensure_ascii=False)
    print(f"  politicians.json: {len(pol_details)} politicians")

    conn.close()
    print(f"\n빌드 완료! → {OUT_DIR}")


if __name__ == "__main__":
    build()
