from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy import and_, func, or_, select

from app.models.feature.value import FeatureValue


class FeatureValueRepository:
    """
    Repository for historical feature values.

    Optimized for bulk operations.
    """

    def __init__(
        self,
        session: Session,
    ) -> None:

        self.session = session

    def bulk_insert(
        self,
        values: list[FeatureValue],
    ) -> None:

        self.session.bulk_save_objects(values)

    def bulk_upsert(
        self,
        values: list[FeatureValue],
        chunk_size: int = 1000,
    ) -> None:
        """
        Insert feature values, or update them in place if a value for
        the same (instrument, feature, trade_date) already exists.

        This makes it safe to re-run the feature pipeline for an
        instrument that has already been processed (e.g. a daily
        re-upload of a CSV with updated/corrected historical rows),
        instead of crashing on the unique constraint or having to
        skip the instrument forever.

        Rows are chunked before building each INSERT statement.
        This isn't just an optimization: SQLite has a hard limit of
        999 bound parameters per statement, so a single INSERT for a
        large batch (e.g. a full historical backfill) would fail --
        each row here uses 6 parameters, so chunk_size=500 stays
        safely under that limit while also keeping each statement a
        reasonable size for Postgres.
        """

        if not values:
            return

        dialect = self.session.bind.dialect.name

        if dialect == "postgresql":
            self._bulk_upsert_postgresql(values, chunk_size)
        elif dialect == "sqlite":
            self._bulk_upsert_sqlite(values, chunk_size)
        else:
            raise NotImplementedError(
                f"bulk_upsert is not implemented for dialect: {dialect}"
            )

    def _bulk_upsert_postgresql(
        self,
        values: list[FeatureValue],
        chunk_size: int,
    ) -> None:
        """
        Builds one real multi-row INSERT (a single VALUES clause
        covering the whole chunk) and sends it in one round-trip via
        the raw DBAPI cursor. Uses plain %s placeholders rather than
        a driver-specific helper (like psycopg2's execute_values) so
        this works with either psycopg2 or psycopg v3 -- the driver
        requirements.txt actually declares.

        SQLAlchemy Core's own statement-compilation approach was
        tried first and abandoned: profiling showed that for
        INSERT ... ON CONFLICT statements specifically, SQLAlchemy's
        automatic multi-row batching optimization doesn't reliably
        engage, so it falls back to the DBAPI's plain executemany()
        -- which, at least under psycopg2, loops single-row INSERTs
        internally regardless of how the statement was built, making
        chunk count irrelevant to throughput.
        """

        connection = self.session.connection()
        raw_connection = connection.connection.dbapi_connection

        cursor = raw_connection.cursor()

        columns = (
            "instrument_id, feature_definition_id, trade_date, "
            "decimal_value, integer_value, boolean_value"
        )

        for start in range(0, len(values), chunk_size):

            chunk = values[start:start + chunk_size]

            placeholders = ", ".join(
                ["(%s, %s, %s, %s, %s, %s)"] * len(chunk)
            )

            sql = f"""
                INSERT INTO feature_values ({columns})
                VALUES {placeholders}
                ON CONFLICT (instrument_id, feature_definition_id, trade_date)
                DO UPDATE SET
                    decimal_value = EXCLUDED.decimal_value,
                    integer_value = EXCLUDED.integer_value,
                    boolean_value = EXCLUDED.boolean_value
                WHERE
                    feature_values.decimal_value IS DISTINCT FROM EXCLUDED.decimal_value
                    OR feature_values.integer_value IS DISTINCT FROM EXCLUDED.integer_value
                    OR feature_values.boolean_value IS DISTINCT FROM EXCLUDED.boolean_value
            """

            params: list = []

            for value in chunk:
                params.extend(
                    [
                        value.instrument_id,
                        value.feature_definition_id,
                        value.trade_date,
                        value.decimal_value,
                        value.integer_value,
                        value.boolean_value,
                    ]
                )

            cursor.execute(sql, params)

        cursor.close()

    def _bulk_upsert_sqlite(
        self,
        values: list[FeatureValue],
        chunk_size: int,
    ) -> None:
        """
        SQLite path (used by the test suite). SQLite has a hard
        999-bound-parameter-per-statement limit, so rows are chunked
        and each chunk is executed via SQLAlchemy Core, which is
        fast enough at test-suite scale.
        """

        from sqlalchemy.dialects.sqlite import insert as build_insert

        statement = build_insert(FeatureValue)

        statement = statement.on_conflict_do_update(
            index_elements=[
                "instrument_id",
                "feature_definition_id",
                "trade_date",
            ],
            set_={
                "decimal_value": statement.excluded.decimal_value,
                "integer_value": statement.excluded.integer_value,
                "boolean_value": statement.excluded.boolean_value,
            },
            # Same "don't rewrite an unchanged row" guard as the
            # Postgres path, kept in step so the tests exercise it.
            where=or_(
                FeatureValue.decimal_value.is_distinct_from(
                    statement.excluded.decimal_value,
                ),
                FeatureValue.integer_value.is_distinct_from(
                    statement.excluded.integer_value,
                ),
                FeatureValue.boolean_value.is_distinct_from(
                    statement.excluded.boolean_value,
                ),
            ),
        )

        rows = [
            {
                "instrument_id": value.instrument_id,
                "feature_definition_id": value.feature_definition_id,
                "trade_date": value.trade_date,
                "decimal_value": value.decimal_value,
                "integer_value": value.integer_value,
                "boolean_value": value.boolean_value,
            }
            for value in values
        ]

        # SQLite: 999 bound params max / 6 params per row -> stay
        # well under that regardless of the caller's chunk_size.
        sqlite_chunk_size = min(chunk_size, 150)

        for start in range(0, len(rows), sqlite_chunk_size):

            chunk = rows[start:start + sqlite_chunk_size]

            self.session.execute(statement, chunk)

    def has_features(
        self,
        instrument_id: int,
    ) -> bool:
        """
        Returns True if the instrument already has
        historical feature values.
        """

        statement = (
            select(
                FeatureValue.id,
            )
            .where(
                FeatureValue.instrument_id == instrument_id,
            )
            .limit(1)
        )

        return self.session.scalar(statement) is not None

    def get_history(
        self,
        instrument_id: int,
        feature_definition_id: int,
    ) -> list[FeatureValue]:

        statement = (
            select(
                FeatureValue,
            )
            .where(
                FeatureValue.instrument_id == instrument_id,
            )
            .where(
                FeatureValue.feature_definition_id == feature_definition_id,
            )
            .order_by(
                FeatureValue.trade_date,
            )
        )

        return list(self.session.scalars(statement))

    def delete_history(
        self,
        instrument_id: int,
    ) -> None:

        statement = select(
            FeatureValue,
        ).where(
            FeatureValue.instrument_id == instrument_id,
        )

        values = self.session.scalars(statement)

        for value in values:
            self.session.delete(value)

    def get_latest_feature_values(
        self,
    ) -> list[FeatureValue]:
        """
       Return the latest FeatureValue row for every
       (instrument_id, feature_definition_id) pair.
       """

        latest = (
            select(
                FeatureValue.instrument_id,
                FeatureValue.feature_definition_id,
                func.max(FeatureValue.trade_date).label("trade_date"),
            )
            .group_by(
                FeatureValue.instrument_id,
                FeatureValue.feature_definition_id,
            )
            .subquery()
        )

        statement = select(FeatureValue).join(
            latest,
            and_(
                FeatureValue.instrument_id == latest.c.instrument_id,
                FeatureValue.feature_definition_id == latest.c.feature_definition_id,
                FeatureValue.trade_date == latest.c.trade_date,
            ),
        )

        return list(self.session.scalars(statement))

    def get_previous_feature_values(
        self,
    ) -> list[FeatureValue]:
        """
        Return the *second*-most-recent FeatureValue row for every
        (instrument_id, feature_definition_id) pair — i.e. the prior
        trading day's value.

        Used to detect crossovers (e.g. price/indicator crossing
        above or below another line), which is how breakout and
        breakdown signals are identified.
        """

        ranked = (
            select(
                FeatureValue,
                func.row_number()
                .over(
                    partition_by=(
                        FeatureValue.instrument_id,
                        FeatureValue.feature_definition_id,
                    ),
                    order_by=FeatureValue.trade_date.desc(),
                )
                .label("rank"),
            )
            .subquery()
        )

        statement = (
            select(FeatureValue)
            .join(
                ranked,
                FeatureValue.id == ranked.c.id,
            )
            .where(ranked.c.rank == 2)
        )

        return list(self.session.scalars(statement))

    def get_history_for_instrument(
        self,
        instrument_id: int,
    ) -> list[tuple[date, str, Decimal | None, int | None, bool | None]]:
        """
        Full feature-value history for one instrument, joined to
        feature definition names, ordered by date. Used to build a
        day-by-day time series for backtesting (walking through
        every historical trading day, not just the latest one).

        Returns (trade_date, feature_name, decimal_value,
        integer_value, boolean_value) tuples.
        """

        from app.models.feature.definition import FeatureDefinition

        statement = (
            select(
                FeatureValue.trade_date,
                FeatureDefinition.name,
                FeatureValue.decimal_value,
                FeatureValue.integer_value,
                FeatureValue.boolean_value,
            )
            .join(
                FeatureDefinition,
                FeatureDefinition.id == FeatureValue.feature_definition_id,
            )
            .where(FeatureValue.instrument_id == instrument_id)
            .order_by(FeatureValue.trade_date.asc())
        )

        return list(self.session.execute(statement).all())

    def get_latest_trade_date_by_instrument(
        self,
    ) -> dict[int, date]:
        """
        Return the latest feature trade_date already stored for
        every instrument_id (across all its features).

        Used to skip reprocessing an instrument's full history when
        its CSV has no new rows since the last sync -- without this,
        every daily sync would recompute every instrument from
        scratch regardless of whether anything changed.
        """

        statement = select(
            FeatureValue.instrument_id,
            func.max(FeatureValue.trade_date),
        ).group_by(
            FeatureValue.instrument_id,
        )

        return dict(self.session.execute(statement).all())