from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.services.feature_sync_service import (
    FeatureSyncService,
)


def main():

    session: Session = SessionLocal()

    try:

        service = FeatureSyncService(
            session=session,
        )

        service.sync()

        print("✅ Feature definitions synchronized successfully.")

    finally:

        session.close()


if __name__ == "__main__":
    main()