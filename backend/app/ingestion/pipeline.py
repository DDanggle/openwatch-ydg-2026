"""Data ingestion pipeline: OpenWatch → SQLite → Analysis."""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3

import httpx

from ..database import get_db, init_db
from .address_parser import find_lawd_code, match_trade_record, parse_address
from .openwatch import (
    fetch_all_assets,
    fetch_all_members,
    normalize_asset,
    normalize_member,
)
from .real_estate import fetch_trades_for_period

logger = logging.getLogger(__name__)


def _upsert_member(conn: sqlite3.Connection, member: dict) -> None:
    conn.execute(
        """
        INSERT INTO politician_master (id, name, party, constituency,
            assembly_terms, latest_elected, birth_year, gender, raw_json)
        VALUES (:id, :name, :party, :constituency,
            :assembly_terms, :latest_elected, :birth_year, :gender, :raw_json)
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name, party=excluded.party,
            constituency=excluded.constituency,
            assembly_terms=excluded.assembly_terms,
            latest_elected=excluded.latest_elected,
            raw_json=excluded.raw_json,
            updated_at=datetime('now')
        """,
        member,
    )


def _upsert_asset(conn: sqlite3.Connection, asset: dict) -> int | None:
    cursor = conn.execute(
        """
        INSERT INTO asset_itemized (politician_id, disclosure_date, disclosure_year,
            asset_type, relation, kind, detail,
            origin_valuation, increased_amount, decreased_amount, current_valuation,
            reason, raw_json)
        VALUES (:politician_id, :disclosure_date, :disclosure_year,
            :asset_type, :relation, :kind, :detail,
            :origin_valuation, :increased_amount, :decreased_amount, :current_valuation,
            :reason, :raw_json)
        ON CONFLICT(politician_id, disclosure_date, asset_type, relation, kind, detail)
        DO UPDATE SET
            origin_valuation=excluded.origin_valuation,
            increased_amount=excluded.increased_amount,
            decreased_amount=excluded.decreased_amount,
            current_valuation=excluded.current_valuation,
            reason=excluded.reason,
            raw_json=excluded.raw_json
        """,
        asset,
    )
    return cursor.lastrowid


async def ingest_members() -> int:
    """Fetch all members from OpenWatch and store in DB."""
    logger.info("Starting member ingestion...")
    raw_members = await fetch_all_members()

    count = 0
    with get_db() as conn:
        for raw in raw_members:
            member = normalize_member(raw)
            _upsert_member(conn, member)
            count += 1

    logger.info(f"Ingested {count} members")
    return count


async def ingest_assets() -> int:
    """Fetch all asset records from OpenWatch and store in DB."""
    logger.info("Starting asset ingestion...")
    raw_assets = await fetch_all_assets()

    count = 0
    with get_db() as conn:
        # Build politician_id lookup from existing members
        members = conn.execute("SELECT id FROM politician_master").fetchall()
        member_ids = {row["id"] for row in members}

        for raw in raw_assets:
            # Try to extract politician_id from the asset record
            politician_id = str(raw.get("nationalAssemblyMemberId", ""))
            if not politician_id or politician_id not in member_ids:
                # Try alternative field names
                politician_id = str(raw.get("memberId", raw.get("id", "")))

            if not politician_id:
                continue

            asset = normalize_asset(raw, politician_id)
            if asset["disclosure_year"] == 0:
                continue

            _upsert_asset(conn, asset)
            count += 1

    logger.info(f"Ingested {count} asset records")
    return count


def compute_yearly_aggregates() -> int:
    """Compute yearly aggregates from asset_itemized into asset_disclosure_yearly."""
    logger.info("Computing yearly aggregates...")

    with get_db() as conn:
        # Clear existing aggregates
        conn.execute("DELETE FROM asset_disclosure_yearly")

        # Insert aggregated data
        conn.execute("""
            INSERT INTO asset_disclosure_yearly (
                politician_id, disclosure_year,
                total_assets, total_debt, net_assets,
                real_estate_total, deposit_total, securities_total,
                self_total, spouse_total, family_total
            )
            SELECT
                politician_id,
                disclosure_year,
                SUM(CASE WHEN asset_type != '채무' THEN current_valuation ELSE 0 END),
                SUM(CASE WHEN asset_type = '채무' THEN current_valuation ELSE 0 END),
                SUM(CASE WHEN asset_type != '채무' THEN current_valuation ELSE 0 END)
                  - SUM(CASE WHEN asset_type = '채무' THEN current_valuation ELSE 0 END),
                SUM(CASE WHEN asset_type IN ('건물','부동산') THEN current_valuation ELSE 0 END),
                SUM(CASE WHEN asset_type = '예금' THEN current_valuation ELSE 0 END),
                SUM(CASE WHEN asset_type = '증권' THEN current_valuation ELSE 0 END),
                SUM(CASE WHEN relation = '본인' AND asset_type != '채무'
                    THEN current_valuation ELSE 0 END),
                SUM(CASE WHEN relation = '배우자'
                    THEN current_valuation ELSE 0 END),
                SUM(CASE WHEN relation != '본인'
                    THEN current_valuation ELSE 0 END)
            FROM asset_itemized
            GROUP BY politician_id, disclosure_year
        """)

        # Compute YoY changes
        conn.execute("""
            UPDATE asset_disclosure_yearly AS cur
            SET yoy_change = cur.net_assets - (
                    SELECT prev.net_assets
                    FROM asset_disclosure_yearly prev
                    WHERE prev.politician_id = cur.politician_id
                      AND prev.disclosure_year = cur.disclosure_year - 1
                ),
                yoy_change_pct = CASE
                    WHEN (SELECT prev.net_assets
                          FROM asset_disclosure_yearly prev
                          WHERE prev.politician_id = cur.politician_id
                            AND prev.disclosure_year = cur.disclosure_year - 1
                         ) != 0
                    THEN (cur.net_assets - (
                        SELECT prev.net_assets
                        FROM asset_disclosure_yearly prev
                        WHERE prev.politician_id = cur.politician_id
                          AND prev.disclosure_year = cur.disclosure_year - 1
                    )) * 100.0 / ABS((
                        SELECT prev.net_assets
                        FROM asset_disclosure_yearly prev
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

        count = conn.execute(
            "SELECT COUNT(*) as c FROM asset_disclosure_yearly"
        ).fetchone()["c"]

    logger.info(f"Computed {count} yearly aggregate records")
    return count


async def match_real_estate_assets() -> int:
    """Match real estate assets with 실거래가 data."""
    logger.info("Starting real estate matching...")

    with get_db() as conn:
        # Get all real estate asset items
        real_estate_items = conn.execute("""
            SELECT id, politician_id, detail, current_valuation, disclosure_year
            FROM asset_itemized
            WHERE asset_type IN ('건물', '부동산')
              AND detail IS NOT NULL
              AND detail != ''
            ORDER BY disclosure_year DESC
        """).fetchall()

    logger.info(f"Found {len(real_estate_items)} real estate items to match")

    matched_count = 0
    # Cache for trade data by lawd_cd
    trade_cache: dict[str, list[dict]] = {}

    with get_db() as conn:
        for item in real_estate_items:
            parsed = parse_address(item["detail"])
            lawd_cd = find_lawd_code(parsed)

            if not lawd_cd:
                continue

            # Fetch trades if not cached
            if lawd_cd not in trade_cache:
                year = item["disclosure_year"]
                # Look at ±6 months around the disclosure year
                start_ym = f"{year - 1}07"
                end_ym = f"{year}06"
                try:
                    trades = await fetch_trades_for_period(
                        lawd_cd, start_ym, end_ym
                    )
                    trade_cache[lawd_cd] = trades
                except Exception as e:
                    logger.warning(f"Failed to fetch trades for {lawd_cd}: {e}")
                    trade_cache[lawd_cd] = []

            trades = trade_cache.get(lawd_cd, [])
            match = match_trade_record(parsed, trades)

            if match.confidence > 0:
                declared = item["current_valuation"]
                estimated = match.trade_price or 0
                gap = estimated - declared
                gap_pct = (gap / declared * 100) if declared > 0 else 0

                conn.execute(
                    """
                    INSERT INTO real_estate_match (
                        asset_item_id, politician_id,
                        sido, sigungu, dong, apartment_name, area_sqm,
                        matched_trade_price, match_confidence, match_method,
                        declared_valuation, estimated_market_value,
                        gap_amount, gap_pct
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(asset_item_id) DO UPDATE SET
                        matched_trade_price=excluded.matched_trade_price,
                        match_confidence=excluded.match_confidence,
                        estimated_market_value=excluded.estimated_market_value,
                        gap_amount=excluded.gap_amount,
                        gap_pct=excluded.gap_pct
                    """,
                    (
                        item["id"],
                        item["politician_id"],
                        parsed.sido,
                        parsed.sigungu,
                        parsed.dong,
                        parsed.apartment_name or match.apartment_name,
                        parsed.area_sqm or match.area_sqm,
                        match.trade_price,
                        match.confidence,
                        match.method,
                        declared,
                        estimated,
                        gap,
                        gap_pct,
                    ),
                )
                matched_count += 1

    logger.info(f"Matched {matched_count} real estate items")
    return matched_count


async def run_full_pipeline(skip_real_estate: bool = False) -> dict[str, int]:
    """Run the complete ingestion pipeline."""
    results: dict[str, int] = {}

    # Step 1: Initialize DB
    init_db()

    # Step 2: Ingest members
    results["members"] = await ingest_members()

    # Step 3: Ingest assets
    results["assets"] = await ingest_assets()

    # Step 4: Compute yearly aggregates
    results["yearly_aggregates"] = compute_yearly_aggregates()

    # Step 5: Match real estate (optional, requires API key)
    if not skip_real_estate:
        results["real_estate_matches"] = await match_real_estate_assets()

    # Step 6: Compute derived metrics (imported from analysis module)
    from ..analysis.growth import compute_all_growth_metrics

    results["derived_metrics"] = compute_all_growth_metrics()

    return results
