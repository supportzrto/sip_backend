from decimal import Decimal

import pytest

from app.indicators.bollinger import BollingerBandsIndicator
from app.indicators.enums import IndicatorType
from tests.helpers.candle_factory import create_candle


def test_invalid_period():

    with pytest.raises(ValueError):
        BollingerBandsIndicator(period=1)


def test_empty_candles():

    indicator = BollingerBandsIndicator()

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

    indicator = BollingerBandsIndicator()

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

    indicator = BollingerBandsIndicator()

    values = indicator.calculate(candles)

    assert len(values) == (
        len(candles)
        - indicator.period
        + 1
    )


def test_band_order():

    candles = []

    for day in range(1, 40):

        candles.append(
            create_candle(
                day,
                Decimal(day),
            )
        )

    indicator = BollingerBandsIndicator()

    values = indicator.calculate(candles)

    for value in values:

        assert value.upper > value.middle
        assert value.middle > value.lower


def test_metadata():

    candles = []

    for day in range(1, 40):

        candles.append(
            create_candle(
                day,
                Decimal(day),
            )
        )

    indicator = BollingerBandsIndicator()

    values = indicator.calculate(candles)

    first = values[0]

    assert first.indicator == IndicatorType.BOLLINGER
    assert first.period == 20
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

    indicator = BollingerBandsIndicator()

    values = indicator.calculate(candles)

    for value in values:

        assert value.upper == Decimal("100.0000")
        assert value.middle == Decimal("100.0000")
        assert value.lower == Decimal("100.0000")