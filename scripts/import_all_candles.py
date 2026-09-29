import time

from app.database.session import SessionLocal
from app.market_data.importer.candle_importer import (
    HistoricalDataImporter,
)
from app.market_data.providers.csv_provider import CSVProvider
from app.repositories.daily_candle_repository import (
    DailyCandleRepository,
)
from app.repositories.instrument_repository import (
    InstrumentRepository,
)


def main() -> None:

    db = SessionLocal()

    start_time = time.time()

    total_candles = 0
    imported_symbols = 0
    failed_symbols = []

    try:

        provider = CSVProvider("data/candles")

        instrument_repository = InstrumentRepository(db)
        candle_repository = DailyCandleRepository(db)

        importer = HistoricalDataImporter(
            provider=provider,
            instrument_repository=instrument_repository,
            candle_repository=candle_repository,
        )

        instruments = instrument_repository.get_all()

        total = len(instruments)

        print()
        print(f"Found {total} instruments.")
        print()

        for index, instrument in enumerate(instruments, start=1):

            try:

                imported = importer.import_daily_candles(
                    instrument.symbol
                )

                total_candles += imported
                imported_symbols += 1

                print(
                    f"[{index}/{total}] "
                    f"{instrument.symbol:<15} "
                    f"✓ {imported} candles"
                )

            except Exception as e:

                db.rollback()

                failed_symbols.append(instrument.symbol)

                print(
                    f"[{index}/{total}] "
                    f"{instrument.symbol:<15} "
                    f"✗ {e}"
                )

        elapsed = time.time() - start_time

        print()
        print("=" * 60)
        print(f"Imported Symbols : {imported_symbols}")
        print(f"Failed Symbols   : {len(failed_symbols)}")
        print(f"Total Candles    : {total_candles}")
        print(f"Elapsed Time     : {elapsed:.2f} seconds")
        print("=" * 60)

        if failed_symbols:

            print()
            print("Failed Symbols:")

            for symbol in failed_symbols:
                print(symbol)

    finally:

        db.close()


if __name__ == "__main__":
    main()