from decimal import Decimal

import pytest

from app.indicators.enums import IndicatorType
from app.indicators.supertrend import SupertrendIndicator
from tests.helpers.candle_factory import create_candle


def test_invalid_period():

    with pytest.raises(ValueError):
        SupertrendIndicator(period=1)


def test_empty_candles():

    indicator = SupertrendIndicator()

    assert indicator.calculate([]) == []


def test_less_than_period():

    candles = []

    for day in range(1, 8):

        candles.append(
            create_candle(
                day,
                Decimal(day),
            )
        )

    indicator = SupertrendIndicator()

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

    indicator = SupertrendIndicator()

    values = indicator.calculate(candles)

    assert len(values) == (
        len(candles)
        - indicator.period
    )


def test_metadata():

    candles = []

    for day in range(1, 40):

        candles.append(
            create_candle(
                day,
                Decimal(day),
            )
        )

    indicator = SupertrendIndicator()

    first = indicator.calculate(candles)[0]

    assert first.indicator == IndicatorType.SUPERTREND
    assert first.period == 10
    assert first.symbol == "TEST"


def test_constant_prices():

    candles = []

    for day in range(1, 40):

        candles.append(
            create_candle(
                day,
                Decimal("100"),
            )
        )

    indicator = SupertrendIndicator()

    values = indicator.calculate(candles)

    assert len(values) > 0

    for value in values:

        assert value.value >= Decimal("0")


def test_trend_boolean():

    candles = []

    for day in range(1, 40):

        candles.append(
            create_candle(
                day,
                Decimal(day),
            )
        )

    indicator = SupertrendIndicator()

    values = indicator.calculate(candles)

    for value in values:

        assert isinstance(
            value.is_bullish,
            bool,
        )