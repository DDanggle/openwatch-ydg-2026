#!/usr/bin/env python3
"""todo_음수괴리검토.csv → DB 반영. action 열 기준으로 처리."""

import csv, sqlite3
from pathlib import Path

CSV_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "todo_음수괴리검토.csv"
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "wealth_tracker.db"

def main():
    conn = sqlite3.connect(str(DB_PATH))
    deleted, fixed, kept = 0, 0, 0
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            action = row.get("action", "").strip().lower()
            match_id = row["match_id"]
            if not action:
                continue
            if action == "delete":
                conn.execute("DELETE FROM real_estate_match WHERE id=?", (match_id,))
                deleted += 1
                print(f"  🗑️ 삭제: {row['name']} {row['apartment_name']}")
            elif action.startswith("fix:"):
                new_eok = float(action.split(":")[1])
                new_won = int(new_eok * 1e8)
                declared = int(float(row["declared_eok"]) * 1e8)
                gap = new_won - declared
                gap_pct = (gap / declared * 100) if declared > 0 else 0
                conn.execute("""
                    UPDATE real_estate_match SET estimated_market_value=?, gap_amount=?, gap_pct=?
                    WHERE id=?
                """, (new_won, gap, round(gap_pct, 2), match_id))
                fixed += 1
                print(f"  🔧 수정: {row['name']} → {new_eok}억 ({gap_pct:+.0f}%)")
            elif action == "keep":
                kept += 1
    conn.commit()
    conn.close()
    print(f"\n삭제: {deleted}건 | 수정: {fixed}건 | 유지: {kept}건")

if __name__ == "__main__":
    main()
