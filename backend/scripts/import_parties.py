#!/usr/bin/env python3
"""todo_정당분류.csv → DB 반영. corrected_party가 채워진 행만 업데이트."""

import csv, sqlite3
from pathlib import Path

CSV_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "todo_정당분류.csv"
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "wealth_tracker.db"

def main():
    conn = sqlite3.connect(str(DB_PATH))
    updated = 0
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            party = row.get("corrected_party", "").strip()
            if not party:
                continue
            conn.execute("UPDATE politician_master SET party=? WHERE id=?", (party, row["id"]))
            updated += 1
            print(f"  ✅ {row['name']} → {party}")
    conn.commit()
    conn.close()
    print(f"\n{updated}명 정당 업데이트 완료")

if __name__ == "__main__":
    main()
