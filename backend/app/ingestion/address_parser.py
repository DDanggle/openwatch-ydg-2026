"""Address parsing and matching for real estate assets — 2026 실데이터용."""

from __future__ import annotations

import csv
import logging
import re
from dataclasses import dataclass
from pathlib import Path

from rapidfuzz import fuzz

logger = logging.getLogger(__name__)

_LAWD_CODE_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "lawd_code.csv"

# ── Regex patterns ──

# 시도 (풀네임)
SIDO_PATTERN = re.compile(
    r"(서울특별시|부산광역시|대구광역시|인천광역시|광주광역시|대전광역시|울산광역시|"
    r"세종특별자치시|경기도|강원특별자치도|강원도|충청북도|충청남도|"
    r"전북특별자치도|전라북도|전라남도|경상북도|경상남도|제주특별자치도)"
)

# 시도 약칭 매핑
SIDO_SHORT = {
    "서울특별시": "서울", "부산광역시": "부산", "대구광역시": "대구",
    "인천광역시": "인천", "광주광역시": "광주", "대전광역시": "대전",
    "울산광역시": "울산", "세종특별자치시": "세종",
    "경기도": "경기", "강원특별자치도": "강원", "강원도": "강원",
    "충청북도": "충북", "충청남도": "충남",
    "전북특별자치도": "전북", "전라북도": "전북",
    "전라남도": "전남", "경상북도": "경북", "경상남도": "경남",
    "제주특별자치도": "제주",
}

# 시군구 - 시도 뒤에서만 매칭
SIGUNGU_PATTERN = re.compile(r"([\w]{1,4}[시군구](?:[\w]{1,4}[구])?)")

# 동/읍/면/리 — 건물, 토지 등 일반명사 제외
DONG_PATTERN = re.compile(r"(?<!건물)(?<!아파트)([\w]{1,8}[동읍면리가로])\b")

# 아파트 단지명
APT_NAME_PATTERN = re.compile(
    r"([\w]+"
    r"(?:아파트|APT|타워|빌|파크|힐스|자이|래미안|푸르지오|"
    r"e편한세상|더샵|아이파크|롯데캐슬|SK뷰|호반써밋|"
    r"센트럴|하이츠|맨션|빌라|주공|한양|현대|삼성|대우|"
    r"LG|두산|코오롱|한화|대림|GS|월드메르디앙|리첸시아|"
    r"헤링턴|캐슬|트라팰리스|팰리스|리체|드림|포레|써밋|"
    r"힐|웰리체|파인|아크로|래미안|"
    r"폴리스|하늘채|리버젠|엘스|원베일리|비스타|위버필드|"
    r"스타시티|선수촌|기자촌|에스티지|시범|훼미리|"
    r"신시가지|미라주|뉴타운|극동|경남|우성|한남더힐|"
    r"슈퍼빌|올림픽|신반포|반포|잠실|목동|여의도|"
    r"건영|화성파크|비바|클래스|에코)[\w]*)"
)

# 면적: 일반 ㎡
AREA_PATTERN = re.compile(r"(\d+\.?\d*)\s*(?:㎡|제곱미터)")
# "중XX.XX㎡" — 전용면적 (공유지분 중 실소유 면적)
AREA_EXCLUSIVE_PATTERN = re.compile(r"중\s*(\d+\.?\d*)\s*(?:㎡|제곱미터)")
# 평 단위
AREA_PYEONG_PATTERN = re.compile(r"(\d+\.?\d*)\s*평")

PYEONG_TO_SQM = 3.305785


@dataclass
class ParsedAddress:
    sido: str | None = None
    sido_short: str | None = None
    sigungu: str | None = None
    dong: str | None = None
    apartment_name: str | None = None
    area_sqm: float | None = None          # 매칭용 면적 (전체 면적)
    exclusive_area_sqm: float | None = None # "중" 뒤의 지분 면적
    total_area_sqm: float | None = None     # 건물 전체 면적 (A㎡중 B㎡의 A)
    share_ratio: float | None = None        # 지분 비율 (B/A), 공유지분일 때만
    raw_text: str = ""


@dataclass
class MatchResult:
    lawd_cd: str | None = None
    apartment_name: str | None = None
    area_sqm: float | None = None
    trade_price: int | None = None
    trade_date: str | None = None
    confidence: float = 0.0
    method: str = "none"


# ── 법정동코드 lookup ──

_lawd_lookup: dict[str, str] | None = None


def _load_lawd_codes() -> dict[str, str]:
    global _lawd_lookup
    if _lawd_lookup is not None:
        return _lawd_lookup

    _lawd_lookup = {}

    if not _LAWD_CODE_PATH.exists():
        logger.warning(f"법정동코드 file not found: {_LAWD_CODE_PATH}")
        return _lawd_lookup

    with open(_LAWD_CODE_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = row.get("법정동코드", "")[:5]
            name = row.get("법정동명", "").strip()
            if code and name and row.get("폐지여부", "존재") == "존재":
                _lawd_lookup[name] = code
                # 짧은 키도 등록
                parts = name.split()
                if len(parts) >= 2:
                    short_key = " ".join(parts[1:])
                    _lawd_lookup[short_key] = code
                    for p in parts[1:]:
                        if p.endswith(("구", "군")):
                            _lawd_lookup[p] = code

    logger.info(f"Loaded {len(_lawd_lookup)} 법정동코드 entries")
    return _lawd_lookup


def parse_address(detail_text: str) -> ParsedAddress:
    """Extract structured address from free-text."""
    if not detail_text:
        return ParsedAddress(raw_text="")

    parsed = ParsedAddress(raw_text=detail_text)

    # 시도
    m = SIDO_PATTERN.search(detail_text)
    if m:
        parsed.sido = m.group(1)
        parsed.sido_short = SIDO_SHORT.get(m.group(1))
        rest_after_sido = detail_text[m.end():]
    else:
        rest_after_sido = detail_text

    # 시군구 (시도 뒤에서만 매칭)
    m = SIGUNGU_PATTERN.search(rest_after_sido)
    if m:
        parsed.sigungu = m.group(1)

    # 동
    m = DONG_PATTERN.search(rest_after_sido)
    if m:
        dong = m.group(1)
        # "건물동", "아파트동" 같은 오탐 필터
        if dong not in ("건물동", "건물", "토지"):
            parsed.dong = dong

    # 아파트명
    m = APT_NAME_PATTERN.search(detail_text)
    if m:
        name = m.group(1)
        # "건물" 같은 잘못된 매칭 필터
        if len(name) > 2 and name not in ("건물", "토지"):
            parsed.apartment_name = name

    # 면적 파싱 — "A㎡중 B㎡" 패턴 감지 (공유지분)
    # 예: "건물 84.98㎡중 42.49㎡" → total=84.98, share=42.49, ratio=0.5
    share_match = re.search(r"(\d+\.?\d*)\s*㎡\s*중\s*(\d+\.?\d*)\s*㎡", detail_text)
    if share_match:
        total = float(share_match.group(1))
        share = float(share_match.group(2))
        parsed.total_area_sqm = total
        parsed.exclusive_area_sqm = share
        parsed.share_ratio = share / total if total > 0 else 1.0
        # 매칭용 면적은 전체 면적 (API가 전체 면적 기준으로 리턴)
        parsed.area_sqm = total
    else:
        m = AREA_PATTERN.search(detail_text)
        if m:
            parsed.area_sqm = float(m.group(1))
            parsed.total_area_sqm = parsed.area_sqm
        else:
            m = AREA_PYEONG_PATTERN.search(detail_text)
            if m:
                parsed.area_sqm = float(m.group(1)) * PYEONG_TO_SQM
                parsed.total_area_sqm = parsed.area_sqm

    return parsed


def find_lawd_code(parsed: ParsedAddress) -> str | None:
    """Find 5-digit 법정동코드."""
    lookup = _load_lawd_codes()
    if not lookup:
        return None

    # 시군구 직접 매칭
    if parsed.sigungu:
        # "서초구" → lookup에서 찾기
        if parsed.sigungu in lookup:
            return lookup[parsed.sigungu]

        # "서울특별시 서초구" 형태
        if parsed.sido:
            full_key = f"{parsed.sido} {parsed.sigungu}"
            if full_key in lookup:
                return lookup[full_key]

        # 시도약칭 + 시군구
        if parsed.sido_short:
            for name, code in lookup.items():
                if parsed.sido_short in name and parsed.sigungu in name:
                    return code

    return None


def match_trade_record(
    parsed: ParsedAddress,
    trades: list[dict],
) -> MatchResult:
    """
    Match a parsed address against trade records.
    Uses exclusive_area_sqm (전용면적) for matching — this is what the API reports.
    """
    if not trades:
        return MatchResult()

    # 매칭에 사용할 면적 (전용면적 우선)
    match_area = parsed.exclusive_area_sqm or parsed.area_sqm
    best = MatchResult()

    for trade in trades:
        trade_apt = trade.get("아파트", "")
        trade_area = trade.get("전용면적_float", 0.0)
        trade_price = trade.get("거래금액_원", 0)
        trade_dong = trade.get("법정동", "")

        if not trade_price:
            continue

        # Tier 1: 아파트명 포함 + 면적 근접
        if parsed.apartment_name and match_area:
            name_match = (
                parsed.apartment_name in trade_apt
                or trade_apt in parsed.apartment_name
                or fuzz.ratio(parsed.apartment_name, trade_apt) > 85
            )
            area_match = abs((match_area or 0) - trade_area) <= 3.0

            if name_match and area_match and trade_price > (best.trade_price or 0):
                best = MatchResult(
                    apartment_name=trade_apt,
                    area_sqm=trade_area,
                    trade_price=trade_price,
                    confidence=0.9,
                    method="exact",
                )
                continue

        # Tier 2: 아파트명 fuzzy
        if parsed.apartment_name and trade_apt:
            ratio = fuzz.ratio(parsed.apartment_name, trade_apt)
            if ratio > 75 and 0.7 > best.confidence:
                best = MatchResult(
                    apartment_name=trade_apt,
                    area_sqm=trade_area,
                    trade_price=trade_price,
                    confidence=0.7,
                    method="fuzzy_name",
                )
                continue

        # Tier 3: 동 + 면적
        if parsed.dong and match_area:
            dong_base = parsed.dong.rstrip("동읍면리가")
            dong_match = dong_base in trade_dong
            area_close = abs((match_area or 0) - trade_area) <= 5.0
            if dong_match and area_close and 0.5 > best.confidence:
                best = MatchResult(
                    apartment_name=trade_apt,
                    area_sqm=trade_area,
                    trade_price=trade_price,
                    confidence=0.5,
                    method="dong_area",
                )

    # Tier 4: 시군구 평균 (최후 수단)
    if best.confidence == 0.0 and trades:
        prices = [t.get("거래금액_원", 0) for t in trades if t.get("거래금액_원", 0) > 0]
        if prices:
            # 면적 비례로 조정
            if match_area and match_area > 0:
                # ㎡당 평균가 * 면적
                area_prices = [
                    (t.get("거래금액_원", 0), t.get("전용면적_float", 1))
                    for t in trades
                    if t.get("거래금액_원", 0) > 0 and t.get("전용면적_float", 0) > 0
                ]
                if area_prices:
                    avg_per_sqm = sum(p / a for p, a in area_prices) / len(area_prices)
                    estimated = int(avg_per_sqm * match_area)
                    best = MatchResult(
                        trade_price=estimated,
                        confidence=0.3,
                        method="sigungu_avg",
                    )
            else:
                avg_price = sum(prices) // len(prices)
                best = MatchResult(
                    trade_price=avg_price,
                    confidence=0.3,
                    method="sigungu_avg",
                )

    return best
