from decimal import Decimal

from app.scanner.schemas import (
    IndicatorSnapshot,
    StockSnapshot,
)


def test_stock_snapshot():

    snapshot = StockSnapshot(

        current=IndicatorSnapshot(
            values={
                "EMA20": Decimal("120"),
            }
        ),

        previous=IndicatorSnapshot(
            values={
                "EMA20": Decimal("115"),
            }
        ),
    )

    assert (
        snapshot.current.values["EMA20"]
        == Decimal("120")
    )

    assert (
        snapshot.previous.values["EMA20"]
        == Decimal("115")
    )