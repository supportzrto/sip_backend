from decimal import Decimal

import pytest

from app.indicators.atr import ATRIndicator
from app.indicators.enums import IndicatorType
from tests.helpers.candle_factory import create_candle


def test_invalid_period():

    with pytest.raises(ValueError):
        ATRIndicator(period=1)


def test_empty_candles():

    indicator = ATRIndicator()

    assert indicator.calculate([]) == []


def test_less_than_period():

    candles = []

    for day in range(1, 10):

        candles.append(
            create_candle(
                day,
                Decimal(day),
            )
        )

    indicator = ATRIndicator()

    assert indicator.calculate(candles) == []


def test_output_length():

    candles = []

    for day in range(1, 40):

        candles.append(
            create_candle(
                day,
                Decimal(day),
            )
        )

    indicator = ATRIndicator()

    values = indicator.calculate(candles)

    assert len(values) == (
        len(candles) - indicator.period
    )


def test_positive_values():

    candles = []

    for day in range(1, 40):

        candles.append(
            create_candle(
                day,
                Decimal(day),
            )
        )

    indicator = ATRIndicator()

    values = indicator.calculate(candles)

    for value in values:

        assert value.value >= Decimal("0")


def test_constant_prices():

    candles = []

    for day in range(1, 40):

        candles.append(
            create_candle(
                day,
                Decimal("100"),
            )
        )

    indicator = ATRIndicator()

    values = indicator.calculate(candles)

    for value in values:

        assert value.value == Decimal("0.0000")


def test_metadata():

    candles = []

    for day in range(1, 40):

        candles.append(
            create_candle(
                day,
                Decimal(day),
            )
        )

    indicator = ATRIndicator()

    values = indicator.calculate(candles)

    first = values[0]

    assert first.indicator == IndicatorType.ATR
    assert first.period == 14
    assert first.symbol == "TEST"