#!/usr/bin/env python3
"""실거래가 매칭 v2 — 품질 개선: 오매칭 방지, 거래일 저장, 중복 제거."""

import asyncio
import json
import logging
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.ingestion.address_parser import find_lawd_code, match_trade_record, parse_address
from app.ingestion.real_estate import fetch_trades_for_period

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "wealth_tracker.db"

START_YM = "202501"
END_YM = "202503"


def _has_apartment_name(detail: str) -> bool:
    """원본 상세에 아파트명이 있는지 확인. 없으면 dong_area 매칭을 신뢰할 수 없음."""
    # "서초동 건물 79㎡" 같은 건 아파트명이 없는 것
    keywords = ["아파트", "APT", "래미안", "자이", "힐스", "파크", "캐슬", "타워",
                "빌", "푸르지오", "더샵", "아이파크", "e편한세상", "SK뷰", "호반",
                "한양", "현대", "삼성", "대우", "두산", "코오롱", "주공",
                "메르디앙", "하이츠", "맨션", "리체", "드림", "포레", "써밋"]
    return any(kw in detail for kw in keywords)


async def main():
    conn = sqlite3.connect(str(DB_PATH), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")

    # 아파트 항목 (전세 제외)
    items = conn.execute("""
        SELECT id, politician_id, detail, current_valuation, relation
        FROM asset_itemized
        WHERE disclosure_year = 2026
          AND asset_type = '건물'
          AND kind LIKE '%아파트%'
          AND detail IS NOT NULL AND detail != ''
          AND kind NOT LIKE '%전세%' AND kind NOT LIKE '%임차%'
    """).fetchall()

    logger.info(f"전체 아파트 항목: {len(items)}건")
    valid_items = items  # 전부 시도 (품질 필터는 매칭 단계에서)

    # LAWD 코드별 그룹핑
    lawd_items: dict[str, list] = {}
    for item in valid_items:
        parsed = parse_address(item["detail"])
        lawd_cd = find_lawd_code(parsed)
        if lawd_cd:
            if lawd_cd not in lawd_items:
                lawd_items[lawd_cd] = []
            lawd_items[lawd_cd].append((item, parsed))

    logger.info(f"LAWD 코드: {len(lawd_items)}개 × 3개월 = {len(lawd_items)*3}회 API")

    conn.execute("DELETE FROM real_estate_match")
    conn.commit()

    matched = 0
    skipped_low_confidence = 0
    skipped_no_apt_match = 0
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

            # 품질 필터
            if match.method == "sigungu_avg":
                skipped_low_confidence += 1
                continue

            # dong_area는 아파트명이 파싱된 경우에만 허용
            if match.method == "dong_area" and not parsed.apartment_name:
                skipped_no_apt_match += 1
                continue

            # sigungu_avg 제외
            if match.confidence < 0.5 or not match.trade_price:
                skipped_low_confidence += 1
                continue

            # 공유지분 보정 후 괴리 계산
            share_ratio = parsed.share_ratio if parsed.share_ratio else 1.0
            test_estimated = int(match.trade_price * share_ratio)
            test_gap_pct = (test_estimated - item["current_valuation"]) / item["current_valuation"] * 100 if item["current_valuation"] > 0 else 0

            # dong_area이면서 음수 괴리 > -30% → 오매칭
            if match.method == "dong_area" and test_gap_pct < -30:
                skipped_low_confidence += 1
                continue

            # 공유지분 보정
            share_ratio = parsed.share_ratio if parsed.share_ratio else 1.0
            estimated = int(match.trade_price * share_ratio)
            declared = item["current_valuation"]
            gap = estimated - declared
            gap_pct = (gap / declared * 100) if declared > 0 else 0

            # 매칭된 실거래의 거래일 추출 (best match의 trade에서)
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
                match.trade_price,  # 원래 실거래가 (보정 전)
                match.confidence, match.method,
                declared, estimated,  # 보정된 추정가
                gap, round(gap_pct, 2),
                json.dumps({"trade_date": trade_date, "share_ratio": share_ratio}, ensure_ascii=False),
            ))
            matched += 1

        conn.commit()

    # 중복 제거: 같은 의원+같은 아파트+같은 동에서 본인/배우자 각각 있으면 → 하나만 남김
    dupes = conn.execute("""
        SELECT GROUP_CONCAT(rm.id) as ids, COUNT(*) as cnt
        FROM real_estate_match rm
        JOIN asset_itemized ai ON rm.asset_item_id = ai.id
        GROUP BY rm.politician_id, rm.apartment_name, rm.dong
        HAVING COUNT(*) > 1
    """).fetchall()

    removed_dupes = 0
    for dupe in dupes:
        ids = dupe["ids"].split(",")
        # 첫 번째(본인)만 남기고 나머지 삭제
        for dup_id in ids[1:]:
            conn.execute("DELETE FROM real_estate_match WHERE id = ?", (dup_id,))
            removed_dupes += 1

    conn.commit()

    # derived_metrics 업데이트
    for row in conn.execute("SELECT DISTINCT politician_id FROM real_estate_match").fetchall():
        pid = row["politician_id"]
        gaps = conn.execute("""
            SELECT AVG(gap_pct) as avg_g, MAX(gap_pct) as max_g
            FROM real_estate_match WHERE politician_id=? AND match_confidence>=0.7
        """, (pid,)).fetchone()
        conn.execute("""
            UPDATE derived_metrics SET avg_gap_pct=?, max_gap_pct=?
            WHERE politician_id=?
        """, (gaps["avg_g"], gaps["max_g"], pid))

    conn.commit()
    conn.close()

    logger.info(f"""
=== 매칭 결과 ===
  전체 아파트 항목: {len(items)}건
  아파트명 있는 항목: {len(valid_items)}건
  최종 매칭: {matched}건
  중복 제거: {removed_dupes}건
  제외 (dong_area 오매칭): {skipped_no_apt_match}건
  제외 (신뢰도 낮음): {skipped_low_confidence}건
""")


if __name__ == "__main__":
    asyncio.run(main())
