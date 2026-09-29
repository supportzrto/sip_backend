import sys

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

    if len(sys.argv) != 2:
        print("Usage:")
        print("python -m scripts.import_candles SYMBOL")
        return

    symbol = sys.argv[1].upper()

    db = SessionLocal()

    try:

        provider = CSVProvider("data/candles")

        

        instrument_repository = InstrumentRepository(db)

        candle_repository = DailyCandleRepository(db)

        importer = HistoricalDataImporter(
            provider=provider,
            instrument_repository=instrument_repository,
            candle_repository=candle_repository,
        )

        imported = importer.import_daily_candles(symbol)

        print()
        print("=" * 60)
        print(f"{symbol}: Imported {imported} candles.")
        print("=" * 60)

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()