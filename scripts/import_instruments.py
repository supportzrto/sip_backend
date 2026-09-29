from app.database.session import SessionLocal
from app.market_data.importer.instrument_importer import (
    InstrumentImporter,
)
from app.market_data.providers.csv_provider import CSVProvider
from app.repositories.instrument_repository import (
    InstrumentRepository,
)


def main() -> None:
    db = SessionLocal()

    try:
        provider = CSVProvider("data/candles")

        repository = InstrumentRepository(db)

        importer = InstrumentImporter(
            provider=provider,
            repository=repository,
        )

        imported = importer.import_instruments()

        print()
        print("=" * 50)
        print(f"Imported {imported} instruments.")
        print("=" * 50)
        print()

    except Exception as e:
        db.rollback()
        raise e

    finally:
        db.close()


if __name__ == "__main__":
    main()