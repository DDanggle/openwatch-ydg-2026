#!/usr/bin/env python3
"""Seed database with realistic mock data for POC development."""

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import get_db, init_db

random.seed(42)

# ── 실제 국회의원 기반 목 데이터 ──

POLITICIANS = [
    {"id": "M001", "name": "박덕흠", "party": "국민의힘", "constituency": "충북 보은·옥천·영동·괴산", "elected": 21},
    {"id": "M002", "name": "정진석", "party": "국민의힘", "constituency": "충남 공주·부여·청양", "elected": 21},
    {"id": "M003", "name": "이상민", "party": "더불어민주당", "constituency": "대전 유성구을", "elected": 21},
    {"id": "M004", "name": "윤관석", "party": "더불어민주당", "constituency": "전북 군산시", "elected": 21},
    {"id": "M005", "name": "김기현", "party": "국민의힘", "constituency": "울산 남구을", "elected": 21},
    {"id": "M006", "name": "추미애", "party": "더불어민주당", "constituency": "비례대표", "elected": 21},
    {"id": "M007", "name": "이재명", "party": "더불어민주당", "constituency": "인천 계양구을", "elected": 21},
    {"id": "M008", "name": "한동훈", "party": "국민의힘", "constituency": "비례대표", "elected": 22},
    {"id": "M009", "name": "조국", "party": "조국혁신당", "constituency": "비례대표", "elected": 22},
    {"id": "M010", "name": "백종헌", "party": "국민의힘", "constituency": "부산 금정구", "elected": 21},
    {"id": "M011", "name": "김태년", "party": "더불어민주당", "constituency": "경기 성남시수정구", "elected": 21},
    {"id": "M012", "name": "주호영", "party": "국민의힘", "constituency": "대구 수성구을", "elected": 21},
    {"id": "M013", "name": "노웅래", "party": "더불어민주당", "constituency": "서울 마포구갑", "elected": 21},
    {"id": "M014", "name": "정우택", "party": "국민의힘", "constituency": "충북 청주시상당구", "elected": 21},
    {"id": "M015", "name": "이낙연", "party": "더불어민주당", "constituency": "서울 종로구", "elected": 21},
    {"id": "M016", "name": "권성동", "party": "국민의힘", "constituency": "강원 강릉시", "elected": 21},
    {"id": "M017", "name": "우원식", "party": "더불어민주당", "constituency": "서울 노원구병", "elected": 21},
    {"id": "M018", "name": "홍준표", "party": "국민의힘", "constituency": "대구 수성구갑", "elected": 21},
    {"id": "M019", "name": "심상정", "party": "진보당", "constituency": "경기 고양시갑", "elected": 21},
    {"id": "M020", "name": "안철수", "party": "국민의힘", "constituency": "서울 노원구갑", "elected": 22},
    {"id": "M021", "name": "김부겸", "party": "더불어민주당", "constituency": "대구 수성구갑", "elected": 20},
    {"id": "M022", "name": "나경원", "party": "국민의힘", "constituency": "서울 동작구을", "elected": 21},
    {"id": "M023", "name": "이인영", "party": "더불어민주당", "constituency": "서울 구로구을", "elected": 21},
    {"id": "M024", "name": "송영길", "party": "더불어민주당", "constituency": "인천 계양구갑", "elected": 21},
    {"id": "M025", "name": "유기홍", "party": "더불어민주당", "constituency": "서울 관악구갑", "elected": 21},
    {"id": "M026", "name": "김진표", "party": "더불어민주당", "constituency": "경기 수원시장안구", "elected": 21},
    {"id": "M027", "name": "정성호", "party": "더불어민주당", "constituency": "경기 양주시", "elected": 21},
    {"id": "M028", "name": "박홍근", "party": "더불어민주당", "constituency": "서울 중랑구갑", "elected": 21},
    {"id": "M029", "name": "이종배", "party": "국민의힘", "constituency": "충북 충주시", "elected": 21},
    {"id": "M030", "name": "서병수", "party": "국민의힘", "constituency": "부산 해운대구갑", "elected": 21},
]

ASSET_TYPES = ["부동산", "건물", "예금", "증권", "채무", "보석류"]
RELATIONS = ["본인", "배우자", "장남", "장녀", "부", "모"]
YEARS = list(range(2016, 2026))

# 부동산 상세 예시
REAL_ESTATE_DETAILS = [
    "서울특별시 강남구 삼성동 래미안아파트 102동 1501호 84.97㎡",
    "서울특별시 서초구 반포동 래미안퍼스티지 전용 59.96㎡",
    "서울특별시 송파구 잠실동 엘스아파트 84.82㎡",
    "부산광역시 해운대구 우동 더샵센트럴파크 115.67㎡",
    "경기도 성남시 분당구 정자동 아이파크 59.99㎡",
    "서울특별시 강남구 대치동 은마아파트 76.79㎡",
    "서울특별시 강남구 압구정동 현대아파트 121.49㎡",
    "서울특별시 용산구 한남동 한남더힐 244.73㎡",
    "경기도 과천시 중앙동 래미안슈르 84.98㎡",
    "대전광역시 유성구 봉명동 한빛아파트 59.94㎡",
    "충북 보은군 보은읍 토지 1,200㎡",
    "충남 공주시 금성동 상가건물",
    "전북 군산시 나운동 상가 2층",
    "부산 금정구 장전동 상가건물 3층",
    "경기 고양시 일산서구 대화동 토지 850㎡",
]


def _gen_base_assets(politician_idx: int) -> dict:
    """Generate base asset profile for a politician."""
    # 다양한 자산 프로필 생성
    profiles = [
        {"re": 300, "dep": 20, "sec": 10, "debt": 50, "growth": 1.15},   # 부동산 중심 고성장
        {"re": 50, "dep": 30, "sec": 80, "debt": 10, "growth": 1.08},    # 증권 중심
        {"re": 150, "dep": 50, "sec": 30, "debt": 20, "growth": 1.12},   # 균형형
        {"re": 500, "dep": 10, "sec": 5, "debt": 100, "growth": 1.20},   # 초고액 부동산
        {"re": 80, "dep": 40, "sec": 20, "debt": 5, "growth": 1.05},     # 안정형
        {"re": 200, "dep": 15, "sec": 50, "debt": 30, "growth": 1.18},   # 고성장 혼합
    ]
    return profiles[politician_idx % len(profiles)]


def seed_politicians(conn):
    """Insert politicians."""
    for p in POLITICIANS:
        conn.execute(
            """INSERT OR REPLACE INTO politician_master
               (id, name, party, constituency, assembly_terms, latest_elected, birth_year, gender, raw_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                p["id"], p["name"], p["party"], p["constituency"],
                json.dumps([p["elected"]]), p["elected"],
                random.randint(1950, 1975), random.choice(["남", "여"]),
                json.dumps(p, ensure_ascii=False),
            ),
        )
    print(f"  의원 {len(POLITICIANS)}명 입력 완료")


def seed_assets(conn):
    """Generate asset items for each politician across years."""
    count = 0
    for idx, p in enumerate(POLITICIANS):
        profile = _gen_base_assets(idx)
        noise = lambda: random.uniform(0.85, 1.15)

        for year in YEARS:
            year_factor = profile["growth"] ** (year - 2016)

            # 부동산
            re_base = int(profile["re"] * year_factor * noise() * 1_0000_0000)
            details = random.sample(REAL_ESTATE_DETAILS, min(3, len(REAL_ESTATE_DETAILS)))

            for i, detail in enumerate(details):
                portion = re_base // len(details)
                relation = RELATIONS[i % 3]  # 본인, 배우자, 장남 순환
                prev = int(portion / profile["growth"]) if year > 2016 else 0
                conn.execute(
                    """INSERT OR REPLACE INTO asset_itemized
                       (politician_id, disclosure_date, disclosure_year, asset_type,
                        relation, kind, detail, origin_valuation, increased_amount,
                        decreased_amount, current_valuation, reason, raw_json)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        p["id"], f"{year}03", year, random.choice(["부동산", "건물"]),
                        relation, "아파트" if "아파트" in detail else "토지/건물",
                        detail, prev, max(0, portion - prev), 0, portion,
                        "시가변동" if year > 2016 else "신규",
                        "{}",
                    ),
                )
                count += 1

            # 예금
            dep = int(profile["dep"] * year_factor * noise() * 1_0000_0000)
            conn.execute(
                """INSERT OR REPLACE INTO asset_itemized
                   (politician_id, disclosure_date, disclosure_year, asset_type,
                    relation, kind, detail, origin_valuation, increased_amount,
                    decreased_amount, current_valuation, reason, raw_json)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    p["id"], f"{year}03", year, "예금",
                    "본인", "예금", "국민은행 외",
                    int(dep / profile["growth"]) if year > 2016 else 0,
                    0, 0, dep, "이자소득 등", "{}",
                ),
            )
            count += 1

            # 증권
            sec = int(profile["sec"] * year_factor * noise() * 1_0000_0000)
            conn.execute(
                """INSERT OR REPLACE INTO asset_itemized
                   (politician_id, disclosure_date, disclosure_year, asset_type,
                    relation, kind, detail, origin_valuation, increased_amount,
                    decreased_amount, current_valuation, reason, raw_json)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    p["id"], f"{year}03", year, "증권",
                    random.choice(["본인", "배우자"]), "주식", "삼성전자 외",
                    int(sec / profile["growth"]) if year > 2016 else 0,
                    0, 0, sec, "시가변동", "{}",
                ),
            )
            count += 1

            # 채무
            debt = int(profile["debt"] * (0.95 ** (year - 2016)) * noise() * 1_0000_0000)
            conn.execute(
                """INSERT OR REPLACE INTO asset_itemized
                   (politician_id, disclosure_date, disclosure_year, asset_type,
                    relation, kind, detail, origin_valuation, increased_amount,
                    decreased_amount, current_valuation, reason, raw_json)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    p["id"], f"{year}03", year, "채무",
                    "본인", "금융기관 대출", "국민은행 담보대출",
                    int(debt / 0.95) if year > 2016 else 0,
                    0, 0, debt, "상환", "{}",
                ),
            )
            count += 1

    print(f"  자산 항목 {count}건 입력 완료")


def seed_real_estate_matches(conn):
    """Generate fake real estate match data."""
    rows = conn.execute("""
        SELECT id, politician_id, detail, current_valuation, disclosure_year
        FROM asset_itemized
        WHERE asset_type IN ('부동산', '건물')
          AND detail LIKE '%아파트%'
        ORDER BY disclosure_year DESC
    """).fetchall()

    count = 0
    for r in rows:
        declared = r["current_valuation"]
        # 실거래가는 신고가보다 10~60% 높게 설정 (현실적 괴리)
        gap_pct = random.uniform(5, 60)
        estimated = int(declared * (1 + gap_pct / 100))

        detail = r["detail"] or ""
        sido = "서울" if "서울" in detail else ("부산" if "부산" in detail else "경기")
        dong = ""
        for token in detail.split():
            if token.endswith("동"):
                dong = token
                break

        apt_name = ""
        for keyword in ["래미안", "엘스", "더샵", "아이파크", "은마", "현대", "한남더힐"]:
            if keyword in detail:
                apt_name = keyword + "아파트"
                break

        conn.execute(
            """INSERT OR REPLACE INTO real_estate_match
               (asset_item_id, politician_id, sido, sigungu, dong,
                apartment_name, area_sqm, matched_trade_price,
                match_confidence, match_method,
                declared_valuation, estimated_market_value,
                gap_amount, gap_pct)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                r["id"], r["politician_id"], sido, "", dong,
                apt_name, random.uniform(59, 150),
                estimated,
                random.choice([0.7, 0.8, 0.9]),
                random.choice(["exact", "fuzzy_name", "dong_area"]),
                declared, estimated,
                estimated - declared, round(gap_pct, 2),
            ),
        )
        count += 1

    print(f"  부동산 매칭 {count}건 입력 완료")


def compute_aggregates(conn):
    """Compute yearly aggregates."""
    conn.execute("DELETE FROM asset_disclosure_yearly")
    conn.execute("""
        INSERT INTO asset_disclosure_yearly (
            politician_id, disclosure_year,
            total_assets, total_debt, net_assets,
            real_estate_total, deposit_total, securities_total,
            self_total, spouse_total, family_total
        )
        SELECT
            politician_id, disclosure_year,
            SUM(CASE WHEN asset_type != '채무' THEN current_valuation ELSE 0 END),
            SUM(CASE WHEN asset_type = '채무' THEN current_valuation ELSE 0 END),
            SUM(CASE WHEN asset_type != '채무' THEN current_valuation ELSE 0 END)
              - SUM(CASE WHEN asset_type = '채무' THEN current_valuation ELSE 0 END),
            SUM(CASE WHEN asset_type IN ('건물','부동산') THEN current_valuation ELSE 0 END),
            SUM(CASE WHEN asset_type = '예금' THEN current_valuation ELSE 0 END),
            SUM(CASE WHEN asset_type = '증권' THEN current_valuation ELSE 0 END),
            SUM(CASE WHEN relation = '본인' AND asset_type != '채무' THEN current_valuation ELSE 0 END),
            SUM(CASE WHEN relation = '배우자' THEN current_valuation ELSE 0 END),
            SUM(CASE WHEN relation != '본인' THEN current_valuation ELSE 0 END)
        FROM asset_itemized
        GROUP BY politician_id, disclosure_year
    """)

    # YoY
    conn.execute("""
        UPDATE asset_disclosure_yearly AS cur
        SET yoy_change = cur.net_assets - (
                SELECT prev.net_assets FROM asset_disclosure_yearly prev
                WHERE prev.politician_id = cur.politician_id
                  AND prev.disclosure_year = cur.disclosure_year - 1
            ),
            yoy_change_pct = CASE
                WHEN (SELECT prev.net_assets FROM asset_disclosure_yearly prev
                      WHERE prev.politician_id = cur.politician_id
                        AND prev.disclosure_year = cur.disclosure_year - 1) != 0
                THEN (cur.net_assets - (
                    SELECT prev.net_assets FROM asset_disclosure_yearly prev
                    WHERE prev.politician_id = cur.politician_id
                      AND prev.disclosure_year = cur.disclosure_year - 1
                )) * 100.0 / ABS((
                    SELECT prev.net_assets FROM asset_disclosure_yearly prev
                    WHERE prev.politician_id = cur.politician_id
                      AND prev.disclosure_year = cur.disclosure_year - 1
                ))
                ELSE 0
            END
        WHERE EXISTS (
            SELECT 1 FROM asset_disclosure_yearly prev
            WHERE prev.politician_id = cur.politician_id
              AND prev.disclosure_year = cur.disclosure_year - 1
        )
    """)

    cnt = conn.execute("SELECT COUNT(*) as c FROM asset_disclosure_yearly").fetchone()["c"]
    print(f"  연도별 집계 {cnt}건 완료")


def compute_metrics(conn):
    """Compute derived metrics."""
    import math, statistics

    politicians = conn.execute(
        "SELECT DISTINCT politician_id FROM asset_disclosure_yearly"
    ).fetchall()

    all_yoy = [r["yoy_change"] for r in conn.execute(
        "SELECT yoy_change FROM asset_disclosure_yearly WHERE yoy_change != 0"
    ).fetchall()]

    median_yoy = statistics.median(all_yoy) if all_yoy else 0
    stdev_yoy = statistics.stdev(all_yoy) if len(all_yoy) > 2 else 1

    count = 0
    for row in politicians:
        pid = row["politician_id"]

        yearly = conn.execute("""
            SELECT * FROM asset_disclosure_yearly
            WHERE politician_id = ? ORDER BY disclosure_year
        """, (pid,)).fetchall()

        if len(yearly) < 2:
            continue

        first, last = yearly[0], yearly[-1]
        years = last["disclosure_year"] - first["disclosure_year"]

        abs_growth = last["net_assets"] - first["net_assets"]
        growth_rate = (abs_growth / abs(first["net_assets"]) * 100) if first["net_assets"] != 0 else 0

        cagr = None
        if years > 0 and first["net_assets"] > 0 and last["net_assets"] > 0:
            try:
                cagr = (math.pow(last["net_assets"] / first["net_assets"], 1/years) - 1) * 100
            except:
                pass

        # Family
        total = last["self_total"] + last["family_total"]
        family_ratio = last["family_total"] / total if total > 0 else 0
        spouse_ratio = last["spouse_total"] / total if total > 0 else 0

        delta_total = last["net_assets"] - first["net_assets"]
        delta_family = last["family_total"] - first["family_total"]
        family_growth_share = max(0, min(1, delta_family / delta_total)) if delta_total > 0 else 0

        # Gap
        gaps = conn.execute("""
            SELECT avg(gap_pct) as avg_g, max(gap_pct) as max_g
            FROM real_estate_match
            WHERE politician_id = ? AND match_confidence >= 0.5
        """, (pid,)).fetchone()

        # Anomaly
        anomaly_score = 0
        flags = {}
        for y in yearly[1:]:
            if stdev_yoy > 0:
                z = abs(y["yoy_change"] - median_yoy) / stdev_yoy
                if z > 2.5:
                    flags["sudden_spike"] = True
                    anomaly_score += min(20 + (z-2.5)*5, 30)

        anomaly_score = min(anomaly_score, 100)

        conn.execute("""
            INSERT OR REPLACE INTO derived_metrics
            (politician_id, analysis_start_year, analysis_end_year,
             cagr, absolute_growth, growth_rate,
             family_contribution_ratio, spouse_contribution_ratio, family_growth_share,
             avg_gap_pct, max_gap_pct,
             anomaly_flags, anomaly_score)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            pid, first["disclosure_year"], last["disclosure_year"],
            cagr, abs_growth, growth_rate,
            family_ratio, spouse_ratio, family_growth_share,
            gaps["avg_g"], gaps["max_g"],
            json.dumps(flags), anomaly_score,
        ))
        count += 1

    print(f"  파생 지표 {count}명 완료")


def main():
    print("=" * 50)
    print("  Mock 데이터 시딩 시작")
    print("=" * 50)

    init_db()

    with get_db() as conn:
        seed_politicians(conn)
        seed_assets(conn)
        seed_real_estate_matches(conn)
        compute_aggregates(conn)
        compute_metrics(conn)

    print("\n" + "=" * 50)
    print("  완료! 서버를 시작하세요:")
    print("  cd backend && uvicorn app.main:app --reload")
    print("=" * 50)


if __name__ == "__main__":
    main()
