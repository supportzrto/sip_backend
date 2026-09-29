from decimal import Decimal
from datetime import date

import pytest

from app.indicators.sma import SMAIndicator
from decimal import Decimal

import pytest
from app.indicators.enums import IndicatorType
from app.indicators.sma import SMAIndicator
from tests.helpers.candle_factory import create_candle
from datetime import date

def test_invalid_period():

    with pytest.raises(ValueError):

        SMAIndicator(period=1)

def test_empty_candles():

    indicator = SMAIndicator(period=20)

    values = indicator.calculate([])

    assert values == []

def test_less_than_period():

    candles = [
        create_candle(1, Decimal("100")),
        create_candle(2, Decimal("101")),
    ]

    indicator = SMAIndicator(period=20)

    values = indicator.calculate(candles)

    assert values == []

def test_sma_values():

    candles = [

        create_candle(1, Decimal("100")),
        create_candle(2, Decimal("110")),
        create_candle(3, Decimal("120")),
        create_candle(4, Decimal("130")),
        create_candle(5, Decimal("140")),

    ]

    indicator = SMAIndicator(period=3)

    values = indicator.calculate(candles)

    assert len(values) == 3

    assert values[0].indicator == IndicatorType.SMA

    assert values[0].period == 3

    assert values[0].symbol == "TEST"

    assert values[0].value == Decimal("110")

    assert values[1].value == Decimal("120")

    assert values[2].value == Decimal("130")

def test_output_length():

    candles = []

    for day in range(1, 31):

        candles.append(
            create_candle(
                day,
                Decimal(day),
            )
        )

    indicator = SMAIndicator(period=10)

    values = indicator.calculate(candles)

    assert len(values) == 21

