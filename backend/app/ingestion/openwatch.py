"""OpenWatch API client for fetching national assembly member and asset data."""

from __future__ import annotations

import asyncio
import json
import logging

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import settings

logger = logging.getLogger(__name__)

_semaphore: asyncio.Semaphore | None = None


def _get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(1)
    return _semaphore


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def _fetch_page(
    client: httpx.AsyncClient,
    path: str,
    params: dict | None = None,
) -> dict:
    """Fetch a single page from OpenWatch API with rate limiting."""
    sem = _get_semaphore()
    async with sem:
        resp = await client.get(
            f"{settings.openwatch_base_url}{path}",
            params=params,
            timeout=30.0,
        )
        resp.raise_for_status()
        await asyncio.sleep(1.0 / settings.openwatch_requests_per_second)
        return resp.json()


async def fetch_all_members(
    age: int | None = None,
    page_size: int = 100,
) -> list[dict]:
    """Fetch all national assembly members, handling pagination."""
    members: list[dict] = []
    page = 1

    async with httpx.AsyncClient() as client:
        while True:
            params: dict = {"page": page, "pageSize": page_size}
            if age is not None:
                params["age"] = age

            data = await _fetch_page(client, "/national-assembly/members", params)

            rows = data.get("rows", [])
            if not rows:
                break

            members.extend(rows)
            total_count = data.get("totalCount", 0)
            logger.info(
                f"Members page {page}: got {len(rows)} rows "
                f"(total so far: {len(members)}/{total_count})"
            )

            if len(members) >= total_count:
                break
            page += 1

    logger.info(f"Fetched {len(members)} members total")
    return members


async def fetch_member_assets(
    client: httpx.AsyncClient,
    member_id: str | None = None,
    date: str | None = None,
    asset_type: str | None = None,
    page_size: int = 100,
) -> list[dict]:
    """Fetch asset records, optionally filtered by member/date/type."""
    assets: list[dict] = []
    page = 1

    while True:
        params: dict = {"page": page, "pageSize": page_size}
        if member_id:
            params["nationalAssemblyMemberId"] = member_id
        if date:
            params["date"] = date
        if asset_type:
            params["type"] = asset_type

        data = await _fetch_page(client, "/national-assembly/assets", params)

        rows = data.get("rows", [])
        if not rows:
            break

        assets.extend(rows)
        total_count = data.get("totalCount", 0)

        if len(assets) >= total_count:
            break
        page += 1

    return assets


async def fetch_all_assets(page_size: int = 100) -> list[dict]:
    """Fetch all asset records across all members."""
    all_assets: list[dict] = []
    page = 1

    async with httpx.AsyncClient() as client:
        while True:
            params: dict = {"page": page, "pageSize": page_size}
            data = await _fetch_page(client, "/national-assembly/assets", params)

            rows = data.get("rows", [])
            if not rows:
                break

            all_assets.extend(rows)
            total_count = data.get("totalCount", 0)
            logger.info(
                f"Assets page {page}: got {len(rows)} rows "
                f"(total so far: {len(all_assets)}/{total_count})"
            )

            if len(all_assets) >= total_count:
                break
            page += 1

    logger.info(f"Fetched {len(all_assets)} asset records total")
    return all_assets


def normalize_member(raw: dict) -> dict:
    """Normalize an OpenWatch member record for DB insertion."""
    return {
        "id": str(raw.get("id", "")),
        "name": raw.get("name", ""),
        "party": raw.get("partyName", ""),
        "constituency": raw.get("electoralDistrict", ""),
        "assembly_terms": json.dumps(
            [raw.get("age")] if raw.get("age") else []
        ),
        "latest_elected": raw.get("age"),
        "birth_year": _extract_birth_year(raw.get("birthdate", "")),
        "gender": raw.get("gender", ""),
        "raw_json": json.dumps(raw, ensure_ascii=False),
    }


def normalize_asset(raw: dict, politician_id: str) -> dict:
    """Normalize an OpenWatch asset record for DB insertion."""
    disclosure_date = str(raw.get("date", ""))
    year = int(disclosure_date[:4]) if len(disclosure_date) >= 4 else 0

    return {
        "politician_id": politician_id,
        "disclosure_date": disclosure_date,
        "disclosure_year": year,
        "asset_type": raw.get("type", ""),
        "relation": raw.get("relation", ""),
        "kind": raw.get("kind", ""),
        "detail": raw.get("detail", ""),
        "origin_valuation": raw.get("originValuation", 0) or 0,
        "increased_amount": raw.get("increasedAmount", 0) or 0,
        "decreased_amount": raw.get("decreasedAmount", 0) or 0,
        "current_valuation": raw.get("currentValuation", 0) or 0,
        "reason": raw.get("reason", ""),
        "raw_json": json.dumps(raw, ensure_ascii=False),
    }


def _extract_birth_year(birthdate: str) -> int | None:
    if not birthdate:
        return None
    try:
        return int(birthdate[:4])
    except (ValueError, IndexError):
        return None
