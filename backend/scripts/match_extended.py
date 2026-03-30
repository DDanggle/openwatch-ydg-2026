#!/usr/bin/env python3
"""확장 매칭: 기존 매칭 안 된 의원만 대상, 1년치 거래 데이터로 재시도 + 미등록 LAWD 추가."""

import asyncio
import json
import logging
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ingestion.address_parser import find_lawd_code, match_trade_record, parse_address
from app.ingestion.real_estate import fetch_trades_for_period

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "wealth_tracker.db"

# 1년치로 확장
START_YM = "202404"
END_YM = "202503"

# 미등록 LAWD 코드 수동 추가 (군 단위)
EXTRA_LAWD = {
    "강원 고성군": "42820", "강원 양구군": "42800", "강원 양양군": "42830",
    "강원 인제군": "42810", "강원 철원군": "42780",
    "경기 연천군": "41800",
    "경남 거창군": "48880", "경남 고성군": "48820", "경남 남해군": "48840",
    "경남 함안군": "48730", "경남 합천군": "48890", "경남 의령군": "48720",
    "경남 창녕군": "48740", "경남 하동군": "48850",
    "경북 청도군": "47830", "경북 의성군": "47730", "경북 영양군": "47760",
    "경북 봉화군": "47920", "경북 울릉군": "47940", "경북 예천군": "47900",
    "경북 청송군": "47750",
    "전남 강진군": "46810", "전남 담양군": "46710", "전남 무안군": "46840",
    "전남 보성군": "46780", "전남 신안군": "46910", "전남 영광군": "46870",
    "전남 완도군": "46890", "전남 장성군": "46880", "전남 장흥군": "46800",
    "전남 진도군": "46900", "전남 함평군": "46860", "전남 화순군": "46790",
    "전북 고창군": "45790", "전북 무주군": "45730", "전북 부안군": "45800",
    "전북 순창군": "45770", "전북 완주군": "45710", "전북 임실군": "45750",
    "전북 장수군": "45740", "전북 진안군": "45720",
    "충남 서천군": "44770", "충남 청양군": "44790",
    "충북 단양군": "43800",
}


async def main():
    conn = sqlite3.connect(str(DB_PATH), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")

    # 기존 매칭 안 된 의원의 아파트만 대상
    already_matched = set(
        r["politician_id"] for r in
        conn.execute("SELECT DISTINCT politician_id FROM real_estate_match").fetchall()
    )

    items = conn.execute("""
        SELECT id, politician_id, detail, current_valuation, relation
        FROM asset_itemized
        WHERE disclosure_year = 2026
          AND asset_type = '건물'
          AND kind LIKE '%아파트%'
          AND detail IS NOT NULL AND detail != ''
          AND kind NOT LIKE '%전세%' AND kind NOT LIKE '%임차%'
    """).fetchall()

    unmatched = [i for i in items if i["politician_id"] not in already_matched]
    logger.info(f"미매칭 아파트 항목: {len(unmatched)}건 (이미 매칭된 {len(already_matched)}명 제외)")

    # LAWD 코드별 그룹핑
    lawd_items: dict[str, list] = {}
    no_lawd = 0
    for item in unmatched:
        parsed = parse_address(item["detail"])
        lawd_cd = find_lawd_code(parsed)

        # 못 찾으면 EXTRA에서 시도
        if not lawd_cd and parsed.sido_short and parsed.sigungu:
            key = f"{parsed.sido_short} {parsed.sigungu}"
            lawd_cd = EXTRA_LAWD.get(key)

        if lawd_cd:
            if lawd_cd not in lawd_items:
                lawd_items[lawd_cd] = []
            lawd_items[lawd_cd].append((item, parsed))
        else:
            no_lawd += 1

    logger.info(f"LAWD 코드: {len(lawd_items)}개 × 12개월 = {len(lawd_items)*12}회 API (1년치)")
    if no_lawd:
        logger.info(f"LAWD 코드 없음: {no_lawd}건")

    matched = 0
    total_lawd = len(lawd_items)

    for idx, (lawd_cd, item_list) in enumerate(lawd_items.items()):
        try:
            trades = await fetch_trades_for_period(lawd_cd, START_YM, END_YM)
            logger.info(f"[{idx+1}/{total_lawd}] {lawd_cd}: {len(trades)}건 거래, {len(item_list)}건 매칭")
        except Exception as e:
            logger.warning(f"[{idx+1}/{total_lawd}] {lawd_cd} 실패: {e}")
            continue

        for item, parsed in item_list:
            match = match_trade_record(parsed, trades)

            if match.method == "dong_area" and not parsed.apartment_name:
                continue
            if match.method == "sigungu_avg":
                continue
            if match.confidence < 0.5 or not match.trade_price:
                continue

            share_ratio = parsed.share_ratio if parsed.share_ratio else 1.0
            estimated = int(match.trade_price * share_ratio)
            declared = item["current_valuation"]
            gap = estimated - declared
            gap_pct = (gap / declared * 100) if declared > 0 else 0

            if match.method == "dong_area" and gap_pct < -30:
                continue

            # 거래일 추출
            trade_date = ""
            for t in trades:
                if t.get("아파트") == match.apartment_name:
                    y = t.get("거래년도", t.get("dealYear", ""))
                    m = t.get("거래월", t.get("dealMonth", ""))
                    d = t.get("거래일", t.get("dealDay", ""))
                    trade_date = f"{y}.{str(m).zfill(2)}" + (f".{str(d).zfill(2)}" if d else "")
                    break

            conn.execute("""
                INSERT OR REPLACE INTO real_estate_match
                (asset_item_id, politician_id, sido, sigungu, dong,
                 apartment_name, area_sqm, matched_trade_price,
                 match_confidence, match_method,
                 declared_valuation, estimated_market_value,
                 gap_amount, gap_pct, raw_trade_json)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                item["id"], item["politician_id"],
                parsed.sido_short, parsed.sigungu, parsed.dong,
                parsed.apartment_name or match.apartment_name,
                parsed.total_area_sqm or parsed.area_sqm or match.area_sqm,
                match.trade_price,
                match.confidence, match.method,
                declared, estimated, gap, round(gap_pct, 2),
                json.dumps({"trade_date": trade_date, "share_ratio": share_ratio}, ensure_ascii=False),
            ))
            matched += 1

        conn.commit()

    # 중복 제거
    dupes = conn.execute("""
        SELECT GROUP_CONCAT(rm.id) as ids, COUNT(*) as cnt
        FROM real_estate_match rm
        JOIN asset_itemized ai ON rm.asset_item_id = ai.id
        GROUP BY rm.politician_id, rm.apartment_name, rm.dong
        HAVING COUNT(*) > 1
    """).fetchall()
    removed = 0
    for d in dupes:
        ids = d["ids"].split(",")
        for dup_id in ids[1:]:
            conn.execute("DELETE FROM real_estate_match WHERE id = ?", (dup_id,))
            removed += 1

    # derived_metrics 업데이트
    for row in conn.execute("SELECT DISTINCT politician_id FROM real_estate_match").fetchall():
        pid = row["politician_id"]
        gaps = conn.execute("""
            SELECT AVG(gap_pct) as a, MAX(gap_pct) as m
            FROM real_estate_match WHERE politician_id=? AND match_confidence>=0.5
        """, (pid,)).fetchone()
        conn.execute("UPDATE derived_metrics SET avg_gap_pct=?, max_gap_pct=? WHERE politician_id=?",
                      (gaps["a"], gaps["m"], pid))

    conn.commit()

    final = conn.execute("SELECT COUNT(*) as c, COUNT(DISTINCT politician_id) as p FROM real_estate_match").fetchone()
    conn.close()

    logger.info(f"""
=== 확장 매칭 결과 ===
  신규 매칭: {matched}건
  중복 제거: {removed}건
  전체 매칭: {final['c']}건 / {final['p']}명
""")


if __name__ == "__main__":
    asyncio.run(main())
