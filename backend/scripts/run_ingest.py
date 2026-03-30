#!/usr/bin/env python3
"""CLI script to run the data ingestion pipeline."""

import asyncio
import logging
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ingestion.pipeline import run_full_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


async def main():
    skip_re = "--skip-real-estate" in sys.argv
    print("=" * 60)
    print("  데이터 수집 파이프라인 시작")
    print(f"  실거래가 매칭: {'건너뜀' if skip_re else '포함'}")
    print("=" * 60)

    results = await run_full_pipeline(skip_real_estate=skip_re)

    print("\n" + "=" * 60)
    print("  수집 완료!")
    for key, count in results.items():
        print(f"  {key}: {count}건")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
