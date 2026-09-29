from decimal import Decimal

from app.scanner.operators import (
    crosses_above,
    crosses_below,
)
from app.scanner.schemas import (
    IndicatorSnapshot,
    StockSnapshot,
)


def test_crosses_above():

    stock = StockSnapshot(

        previous=IndicatorSnapshot(
            values={
                "EMA20": Decimal("95"),
                "EMA50": Decimal("100"),
            }
        ),

        current=IndicatorSnapshot(
            values={
                "EMA20": Decimal("105"),
                "EMA50": Decimal("100"),
            }
        ),
    )

    assert crosses_above(
        stock,
        "EMA20",
        "EMA50",
    )


def test_crosses_below():

    stock = StockSnapshot(

        previous=IndicatorSnapshot(
            values={
                "EMA20": Decimal("105"),
                "EMA50": Decimal("100"),
            }
        ),

        current=IndicatorSnapshot(
            values={
                "EMA20": Decimal("95"),
                "EMA50": Decimal("100"),
            }
        ),
    )

    assert crosses_below(
        stock,
        "EMA20",
        "EMA50",
    )