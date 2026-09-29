from decimal import Decimal

import pytest

from app.indicators.ema import EMAIndicator
from app.indicators.enums import IndicatorType
from app.indicators.sma import SMAIndicator
from tests.helpers.candle_factory import create_candle


def test_invalid_period():

    with pytest.raises(ValueError):
        EMAIndicator(period=1)


def test_empty_candles():

    indicator = EMAIndicator(period=5)

    assert indicator.calculate([]) == []


def test_less_than_period():

    candles = [
        create_candle(1, Decimal("100")),
        create_candle(2, Decimal("110")),
    ]

    indicator = EMAIndicator(period=5)

    assert indicator.calculate(candles) == []


def test_first_ema_equals_first_sma():

    candles = []

    for day in range(1, 31):

        candles.append(
            create_candle(
                day,
                Decimal(day),
            )
        )

    sma = SMAIndicator(period=10)
    ema = EMAIndicator(period=10)

    sma_values = sma.calculate(candles)
    ema_values = ema.calculate(candles)

    assert ema_values[0].value == sma_values[0].value


def test_output_length():

    candles = []

    for day in range(1, 31):

        candles.append(
            create_candle(
                day,
                Decimal(day),
            )
        )

    indicator = EMAIndicator(period=10)

    values = indicator.calculate(candles)

    assert len(values) == 21


def test_constant_prices():

    candles = []

    for day in range(1, 31):

        candles.append(
            create_candle(
                day,
                Decimal("100"),
            )
        )

    indicator = EMAIndicator(period=10)

    values = indicator.calculate(candles)

    for value in values:

        assert value.value == Decimal("100.0000")


def test_metadata():

    candles = []

    for day in range(1, 15):

        candles.append(
            create_candle(
                day,
                Decimal(day),
            )
        )

    indicator = EMAIndicator(period=5)

    values = indicator.calculate(candles)

    assert values[0].indicator == IndicatorType.EMA
    assert values[0].period == 5
    assert values[0].symbol == "TEST"