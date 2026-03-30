#!/usr/bin/env python3
"""수동입력_미매칭.csv → DB 반영. 실거래추정_억 열이 채워진 행만 import."""

import csv, json, sqlite3, sys
from pathlib import Path

CSV_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "수동입력_미매칭.csv"
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "wealth_tracker.db"

def main():
    if not CSV_PATH.exists():
        print(f"CSV 없음: {CSV_PATH}")
        return

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    imported = 0
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            est = row.get("실거래추정_억", "").strip()
            if not est:
                continue

            try:
                est_won = int(float(est) * 1_0000_0000)
            except ValueError:
                print(f"  ⚠️ 숫자 변환 실패: {row['의원명']} → '{est}'")
                continue

            asset_id = int(row["asset_id"])
            politician_id = row["politician_id"]
            apt_name = row.get("아파트명_정정", "").strip() or None
            trade_date = row.get("거래일", "").strip() or ""
            memo = row.get("출처_메모", "").strip() or "수동입력"

            # 신고가 가져오기
            item = conn.execute("SELECT current_valuation FROM asset_itemized WHERE id=?", (asset_id,)).fetchone()
            if not item:
                print(f"  ⚠️ asset_id {asset_id} 없음")
                continue

            declared = item["current_valuation"]
            gap = est_won - declared
            gap_pct = (gap / declared * 100) if declared > 0 else 0

            conn.execute("""
                INSERT OR REPLACE INTO real_estate_match
                (asset_item_id, politician_id, apartment_name, area_sqm,
                 matched_trade_price, match_confidence, match_method,
                 declared_valuation, estimated_market_value,
                 gap_amount, gap_pct, raw_trade_json)
                VALUES (?,?,?,NULL,?,0.6,'manual_csv',?,?,?,?,?)
            """, (
                asset_id, politician_id, apt_name, est_won,
                declared, est_won, gap, round(gap_pct, 2),
                json.dumps({"trade_date": trade_date, "source": memo}, ensure_ascii=False),
            ))
            imported += 1
            print(f"  ✅ {row['의원명']} | 신고 {declared/1e8:.1f}억 → 추정 {est}억 ({gap_pct:+.0f}%)")

    conn.commit()
    final = conn.execute("SELECT COUNT(*) as c, COUNT(DISTINCT politician_id) as p FROM real_estate_match").fetchone()
    conn.close()
    print(f"\nimport 완료: {imported}건 추가 | 전체: {final['c']}건 / {final['p']}명")

if __name__ == "__main__":
    main()
