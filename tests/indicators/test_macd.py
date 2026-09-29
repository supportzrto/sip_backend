from decimal import Decimal

import pytest

from app.indicators.enums import IndicatorType
from app.indicators.macd import MACDIndicator
from tests.helpers.candle_factory import create_candle


def test_invalid_periods():

    with pytest.raises(ValueError):

        MACDIndicator(
            fast_period=26,
            slow_period=12,
        )


def test_empty_candles():

    indicator = MACDIndicator()

    assert indicator.calculate([]) == []


def test_less_than_slow_period():

    candles = []

    for day in range(1, 20):

        candles.append(
            create_candle(
                day,
                Decimal(day),
            )
        )

    indicator = MACDIndicator()

    assert indicator.calculate(candles) == []


def test_constant_prices():

    candles = []

    for day in range(1, 60):

        candles.append(
            create_candle(
                day,
                Decimal("100"),
            )
        )

    indicator = MACDIndicator()

    values = indicator.calculate(candles)

    assert len(values) > 0

    for value in values:

        assert value.macd == Decimal("0.0000")
        assert value.signal == Decimal("0.0000")
        assert value.histogram == Decimal("0.0000")


def test_metadata():

    candles = []

    for day in range(1, 60):

        candles.append(
            create_candle(
                day,
                Decimal(day),
            )
        )

    indicator = MACDIndicator()

    values = indicator.calculate(candles)

    first = values[0]

    assert first.indicator == IndicatorType.MACD

    assert first.fast_period == 12
    assert first.slow_period == 26
    assert first.signal_period == 9

    assert first.symbol == "TEST"


def test_histogram_identity():

    candles = []

    for day in range(1, 60):

        candles.append(
            create_candle(
                day,
                Decimal(day),
            )
        )

    indicator = MACDIndicator()

    values = indicator.calculate(candles)

    for value in values:

        assert value.histogram == (
            value.macd - value.signal
        )


def test_output_length():

    candles = []

    for day in range(1, 60):

        candles.append(
            create_candle(
                day,
                Decimal(day),
            )
        )

    indicator = MACDIndicator()

    values = indicator.calculate(candles)

    expected = (
        len(candles)
        - indicator.slow_period
        - indicator.signal_period
        + 2
    )

    assert len(values) == expected