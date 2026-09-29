from decimal import Decimal

import pytest

from app.indicators.adx import ADXIndicator
from app.indicators.enums import IndicatorType
from tests.helpers.candle_factory import create_candle


def test_invalid_period():

    with pytest.raises(ValueError):
        ADXIndicator(period=1)


def test_empty_candles():

    indicator = ADXIndicator()

    assert indicator.calculate([]) == []


def test_less_than_period():

    candles = []

    for day in range(1, 20):

        candles.append(
            create_candle(
                day,
                Decimal(day),
            )
        )

    indicator = ADXIndicator()

    assert indicator.calculate(candles) == []


def test_output_length():

    candles = []

    for day in range(1, 60):

        candles.append(
            create_candle(
                day,
                Decimal(day),
            )
        )

    indicator = ADXIndicator()

    values = indicator.calculate(candles)

    expected = (
        len(candles)
        - (indicator.period * 2)
        + 1
    )

    assert len(values) == expected


def test_range():

    candles = []

    for day in range(1, 60):

        candles.append(
            create_candle(
                day,
                Decimal(day),
            )
        )

    indicator = ADXIndicator()

    values = indicator.calculate(candles)

    for value in values:

        assert Decimal("0") <= value.value <= Decimal("100")


def test_metadata():

    candles = []

    for day in range(1, 60):

        candles.append(
            create_candle(
                day,
                Decimal(day),
            )
        )

    indicator = ADXIndicator()

    values = indicator.calculate(candles)

    first = values[0]

    assert first.indicator == IndicatorType.ADX
    assert first.period == 14
    assert first.symbol == "TEST"


def test_constant_prices():

    candles = []

    for day in range(1, 60):

        candles.append(
            create_candle(
                day,
                Decimal("100"),
            )
        )

    indicator = ADXIndicator()

    values = indicator.calculate(candles)

    for value in values:

        assert value.value == Decimal("0.0000")