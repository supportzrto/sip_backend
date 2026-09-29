from __future__ import annotations

from decimal import Decimal

from app.models.feature.snapshot import FeatureSnapshot
from app.scanner.enums import IndicatorField
from app.scanner.schemas import (
    IndicatorSnapshot,
    StockSnapshot,
)


class SnapshotMapper:
    """
    Maps FeatureSnapshot rows into a StockSnapshot.
    """

    def map(
        self,
        rows: list[FeatureSnapshot],
    ) -> StockSnapshot:

        if not rows:
            raise ValueError(
                "Feature snapshot rows cannot be empty."
            )

        values: dict[
            IndicatorField,
            Decimal,
        ] = {}

        for row in rows:

            try:
                field = IndicatorField(
                    row.feature_definition.name
                )

            except ValueError:
                # Ignore unknown features that the scanner
                # doesn't support yet.
                continue

            value = self._extract_value(row)

            if isinstance(value, Decimal):
                values[field] = value

        return StockSnapshot(

            current=IndicatorSnapshot(
                values=values,
            )

        )

    @staticmethod
    def _extract_value(
        row: FeatureSnapshot,
    ) -> Decimal | int | bool | None:

        if row.decimal_value is not None:
            return row.decimal_value

        if row.integer_value is not None:
            return row.integer_value

        if row.boolean_value is not None:
            return row.boolean_value

        return None