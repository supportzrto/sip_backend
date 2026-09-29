from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.repositories.feature_value_repository import (
    FeatureValueRepository,
)
from app.repositories.snapshot_repository import (
    FeatureSnapshotRepository,
)
from app.services.snapshot_updater import SnapshotUpdater


def rebuild_snapshots() -> None:
    """
    Rebuild the feature_snapshot table from existing
    historical feature_values.

    This command is useful when:
    - Snapshot table is empty
    - Snapshot table needs rebuilding
    - Feature values already exist
    """

    session: Session = SessionLocal()

    try:
        feature_value_repository = FeatureValueRepository(session)
        snapshot_repository = FeatureSnapshotRepository(session)

        snapshot_updater = SnapshotUpdater(
            repository=snapshot_repository,
        )

        print("=" * 70)
        print("Rebuilding Feature Snapshots")
        print("=" * 70)

        feature_values = (
            feature_value_repository.get_latest_feature_values()
        )

        print(f"Latest Feature Values : {len(feature_values):,}")

        snapshot_updater.update(feature_values)

        session.commit()

        print()
        print("=" * 70)
        print("Snapshot Rebuild Complete")
        print("=" * 70)
        print(f"Snapshots Written : {len(feature_values):,}")

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()


if __name__ == "__main__":
    rebuild_snapshots()