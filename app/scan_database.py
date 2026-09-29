from __future__ import annotations

import time

from app.database.session import SessionLocal
from app.repositories.snapshot_repository import (
    FeatureSnapshotRepository,
)
from app.scanner.engine import ScannerEngine
from app.scanner.loaders.snapshot_loader import SnapshotLoader
from app.scanner.mappers.snapshot_mapper import SnapshotMapper
from app.scanner.strategies import SwingStrategy


def main() -> None:

    start = time.perf_counter()

    print("=" * 80)
    print("DATABASE MARKET SCANNER")
    print("=" * 80)

    session = SessionLocal()

    try:

        repository = FeatureSnapshotRepository(session)

        mapper = SnapshotMapper()

        loader = SnapshotLoader(
            repository=repository,
            mapper=mapper,
        )

        engine = ScannerEngine()

        strategy = SwingStrategy()

        request = strategy.build_request()

        print("\nLoading feature snapshots...\n")

        stocks = loader.load()

        print(f"Loaded {len(stocks)} stocks\n")

        print("Running scanner...\n")

        results = engine.scan(
            stocks=stocks,
            request=request,
        )

        elapsed = time.perf_counter() - start

        print("=" * 80)
        print("SCAN RESULTS")
        print("=" * 80)

        if results:

            for result in results:

                print(f"✓ {result.symbol}")

        else:

            print("No matching stocks found.")

        print("\n" + "=" * 80)
        print(f"Stocks Loaded : {len(stocks)}")
        print(f"Matches Found : {len(results)}")
        print(f"Completed In  : {elapsed:.2f} seconds")
        print("=" * 80)

    finally:

        session.close()


if __name__ == "__main__":
    main()