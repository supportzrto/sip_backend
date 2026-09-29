from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, joinedload

from app.models.feature.snapshot import FeatureSnapshot


class FeatureSnapshotRepository:
    """
    Repository for latest feature snapshots.

    One row exists for every:
        instrument + feature
    """

    def __init__(
        self,
        session: Session,
    ) -> None:
        self.session = session

    def bulk_upsert(
        self,
        snapshots: list[FeatureSnapshot],
    ) -> None:
        """
        Insert new snapshots or update existing ones.

        Uses PostgreSQL native UPSERT.
        """

        print(f"bulk_upsert received: {len(snapshots)} snapshots")

        if not snapshots:
            return

        values = []

        for snapshot in snapshots:

            values.append(
                {
                    "instrument_id": snapshot.instrument_id,
                    "feature_definition_id": snapshot.feature_definition_id,
                    "trade_date": snapshot.trade_date,
                    "decimal_value": snapshot.decimal_value,
                    "integer_value": snapshot.integer_value,
                    "boolean_value": snapshot.boolean_value,
                }
            )

        statement = insert(
            FeatureSnapshot
        ).values(values)

        statement = statement.on_conflict_do_update(

            constraint="uq_feature_snapshot",

            set_={
                "trade_date": statement.excluded.trade_date,
                "decimal_value": statement.excluded.decimal_value,
                "integer_value": statement.excluded.integer_value,
                "boolean_value": statement.excluded.boolean_value,
            },
        )

        self.session.execute(statement)

        print("UPSERT SQL executed")

    def exists(
        self,
        instrument_id: int,
    ) -> bool:

        statement = (

            select(
                FeatureSnapshot.id,
            )

            .where(
                FeatureSnapshot.instrument_id == instrument_id,
            )

            .limit(1)

        )

        return self.session.scalar(statement) is not None

    def get_snapshot(
        self,
        instrument_id: int,
    ) -> list[FeatureSnapshot]:

        statement = (

            select(
                FeatureSnapshot,
            )

            .where(
                FeatureSnapshot.instrument_id == instrument_id,
            )

            .order_by(
                FeatureSnapshot.feature_definition_id,
            )

        )

        return list(
            self.session.scalars(statement)
        )

    def get_feature(
        self,
        instrument_id: int,
        feature_definition_id: int,
    ) -> FeatureSnapshot | None:

        statement = (

            select(
                FeatureSnapshot,
            )

            .where(
                FeatureSnapshot.instrument_id == instrument_id,
            )

            .where(
                FeatureSnapshot.feature_definition_id
                == feature_definition_id,
            )

        )

        return self.session.scalar(statement)

    def delete_snapshot(
        self,
        instrument_id: int,
    ) -> None:

        statement = (

            delete(
                FeatureSnapshot,
            )

            .where(
                FeatureSnapshot.instrument_id
                == instrument_id,
            )

        )

        self.session.execute(statement)


    def get_all(
        self,
    ) -> list[FeatureSnapshot]:
        """
        Return the latest feature snapshot rows
        for all instruments with required relationships loaded.
        """

        statement = (
            select(FeatureSnapshot)
            .options(
                joinedload(FeatureSnapshot.feature_definition),
                joinedload(FeatureSnapshot.instrument),
            )
            .order_by(
                FeatureSnapshot.instrument_id,
                FeatureSnapshot.feature_definition_id,
            )
        )

        return list(
            self.session.scalars(statement)
        )