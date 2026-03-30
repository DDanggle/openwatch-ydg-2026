"""국토교통부 아파트 매매 실거래가 API client + 캐시."""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
from xml.etree import ElementTree

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

import sqlite3

from ..config import settings

logger = logging.getLogger(__name__)

BASE_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade"

# 영문 → 한글 필드 매핑 (새 API → 기존 코드 호환)
FIELD_MAP = {
    "dealAmount": "거래금액",
    "umdNm": "법정동",
    "aptNm": "아파트",
    "excluUseAr": "전용면적",
    "dealYear": "거래년도",
    "dealMonth": "거래월",
    "dealDay": "거래일",
    "floor": "층",
    "buildYear": "건축년도",
    "aptDong": "아파트동",
    "sggCd": "지역코드",
    "jibun": "지번",
}

_semaphore: asyncio.Semaphore | None = None


def _get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(1)
    return _semaphore


def _get_cache_conn() -> sqlite3.Connection:
    """Separate connection for cache to avoid locking main connection."""
    conn = sqlite3.connect(settings.database_path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _check_cache(lawd_cd: str, deal_ymd: str) -> list[dict] | None:
    try:
        conn = _get_cache_conn()
        row = conn.execute(
            "SELECT response_json FROM trade_data_cache WHERE lawd_cd=? AND deal_ymd=?",
            (lawd_cd, deal_ymd),
        ).fetchone()
        conn.close()
        if row and row["response_json"]:
            return json.loads(row["response_json"])
    except Exception:
        pass
    return None


def _save_cache(lawd_cd: str, deal_ymd: str, records: list[dict]) -> None:
    try:
        conn = _get_cache_conn()
        conn.execute(
            """INSERT OR REPLACE INTO trade_data_cache (lawd_cd, deal_ymd, response_json)
               VALUES (?, ?, ?)""",
            (lawd_cd, deal_ymd, json.dumps(records, ensure_ascii=False)),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning(f"Cache save failed: {e}")


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def fetch_apartment_trades(
    lawd_cd: str,
    deal_ymd: str,
    use_cache: bool = True,
) -> list[dict]:
    """
    Fetch apartment trade records.

    Args:
        lawd_cd: 5-digit 법정동코드 (e.g., "11650" for 서초구)
        deal_ymd: YYYYMM (e.g., "202501")
        use_cache: 캐시 사용 여부
    """
    # 캐시 확인
    if use_cache:
        cached = _check_cache(lawd_cd, deal_ymd)
        if cached is not None:
            logger.debug(f"Cache hit: {lawd_cd}/{deal_ymd} ({len(cached)} records)")
            return cached

    sem = _get_semaphore()
    async with sem:
        params = {
            "serviceKey": settings.real_estate_api_key,
            "LAWD_CD": lawd_cd,
            "DEAL_YMD": deal_ymd,
            "pageNo": 1,
            "numOfRows": 1000,
        }

        async with httpx.AsyncClient() as client:
            resp = await client.get(BASE_URL, params=params, timeout=30.0)
            resp.raise_for_status()

        await asyncio.sleep(1.0 / settings.real_estate_requests_per_second)

        records = _parse_xml_response(resp.text)

        # 캐시 저장
        if use_cache:
            _save_cache(lawd_cd, deal_ymd, records)

        return records


def _parse_xml_response(xml_text: str) -> list[dict]:
    """Parse the XML response from 국토부 API."""
    records: list[dict] = []

    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError:
        logger.error("Failed to parse XML response")
        return records

    # 에러 체크
    result_code = root.findtext(".//resultCode")
    if result_code and result_code != "000" and result_code != "00":
        result_msg = root.findtext(".//resultMsg")
        logger.error(f"API error: {result_code} - {result_msg}")
        return records

    items = root.findall(".//item")
    for item in items:
        record = {}
        for child in item:
            tag = child.tag.strip()
            text = (child.text or "").strip()
            record[tag] = text

        # 영문 → 한글 필드 매핑
        for eng, kor in FIELD_MAP.items():
            if eng in record and kor not in record:
                record[kor] = record[eng]

        # 거래금액 → 원 단위 변환
        raw_price = record.get("거래금액", "")
        try:
            price_str = raw_price.replace(",", "").strip()
            record["거래금액_원"] = int(price_str) * 10_000
        except (ValueError, AttributeError):
            record["거래금액_원"] = 0

        # 전용면적 → float
        try:
            record["전용면적_float"] = float(record.get("전용면적", "0"))
        except (ValueError, TypeError):
            record["전용면적_float"] = 0.0

        records.append(record)

    logger.info(f"Parsed {len(records)} trade records")
    return records


async def fetch_trades_for_period(
    lawd_cd: str,
    start_ym: str,
    end_ym: str,
) -> list[dict]:
    """Fetch trades for a range of months (최근 1년)."""
    start_y, start_m = int(start_ym[:4]), int(start_ym[4:6])
    end_y, end_m = int(end_ym[:4]), int(end_ym[4:6])

    all_trades: list[dict] = []
    y, m = start_y, start_m

    while (y, m) <= (end_y, end_m):
        deal_ymd = f"{y:04d}{m:02d}"
        try:
            trades = await fetch_apartment_trades(lawd_cd, deal_ymd)
            all_trades.extend(trades)
        except Exception as e:
            logger.warning(f"Failed to fetch trades for {lawd_cd}/{deal_ymd}: {e}")

        m += 1
        if m > 12:
            m = 1
            y += 1

    return all_trades
