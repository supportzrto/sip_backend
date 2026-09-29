from decimal import Decimal
from datetime import date

from app.indicators.enums import IndicatorType
from app.indicators.schemas import IndicatorValue
from app.indicators.snapshot_builder import SnapshotBuilder


def test_snapshot_builder():

    builder = SnapshotBuilder()

    results = {

        "EMA_20": [

            IndicatorValue(

                symbol="TEST",

                trade_date=date.today(),

                indicator=IndicatorType.EMA,

                period=20,

                value=Decimal("100"),

            ),

            IndicatorValue(

                symbol="TEST",

                trade_date=date.today(),

                indicator=IndicatorType.EMA,

                period=20,

                value=Decimal("105"),

            ),

        ]

    }

    snapshot = builder.build(results)

    assert (
        snapshot.current.values["EMA20"]
        == Decimal("105")
    )

    assert (
        snapshot.previous.values["EMA20"]
        == Decimal("100")
    )