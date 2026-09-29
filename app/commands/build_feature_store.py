from sqlalchemy.orm import Session

from app.config.settings import settings
from app.database.session import SessionLocal
from app.services.market_data_sync_service import MarketDataSyncService


def main() -> None:

    session: Session = SessionLocal()

    try:

        service = MarketDataSyncService(
            session=session,
            data_directory=settings.DATA_DIRECTORY,
        )

        service.sync()

    except Exception:

        session.rollback()
        raise

    finally:

        session.close()


if __name__ == "__main__":
    main()