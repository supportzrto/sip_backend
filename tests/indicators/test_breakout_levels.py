from decimal import Decimal

import pytest

from app.indicators.breakout_levels import (
    HighestHighIndicator,
    LowestLowIndicator,
)
from app.indicators.enums import IndicatorType
from tests.helpers.candle_factory import create_candle


def test_invalid_period():

    with pytest.raises(ValueError):
        HighestHighIndicator(period=1)

    with pytest.raises(ValueError):
        LowestLowIndicator(period=1)


def test_empty_candles():

    assert HighestHighIndicator(period=5).calculate([]) == []
    assert LowestLowIndicator(period=5).calculate([]) == []


def test_not_enough_candles_returns_empty():

    candles = [
        create_candle(i, Decimal("100"), high=Decimal("100"), low=Decimal("100"))
        for i in range(1, 4)
    ]

    # period=5, only 3 candles -> not even one full window
    assert HighestHighIndicator(period=5).calculate(candles) == []


def test_highest_high_excludes_current_day():
    """
    The window must be lagged (exclude today) -- otherwise a
    breakout could never actually trigger, since today's own high
    is always part of "today's high vs the window including today".
    """

    highs = [10, 20, 30, 15, 12]  # day 5 (12) is lower than day 3's 30

    candles = [
        create_candle(i + 1, Decimal(str(h)), high=Decimal(str(h)))
        for i, h in enumerate(highs)
    ]

    indicator = HighestHighIndicator(period=3)
    results = indicator.calculate(candles)

    # First value corresponds to day 4 (index 3): window = days 1-3 = [10,20,30] -> 30
    assert results[0].value == Decimal("30")

    # Second value corresponds to day 5 (index 4): window = days 2-4 = [20,30,15] -> 30
    assert results[1].value == Decimal("30")

    assert len(results) == 2
    assert results[0].indicator == IndicatorType.HIGHEST
    assert results[0].period == 3


def test_lowest_low_excludes_current_day():

    lows = [10, 5, 8, 20, 3]

    candles = [
        create_candle(i + 1, Decimal(str(v)), low=Decimal(str(v)))
        for i, v in enumerate(lows)
    ]

    indicator = LowestLowIndicator(period=3)
    results = indicator.calculate(candles)

    # Day 4: window = days 1-3 = [10,5,8] -> 5
    assert results[0].value == Decimal("5")

    # Day 5: window = days 2-4 = [5,8,20] -> 5
    assert results[1].value == Decimal("5")

    assert results[0].indicator == IndicatorType.LOWEST


def test_breakout_scenario_close_crosses_above_highest_high():
    """
    Sanity check matching the real use case: a close that's higher
    than every high in the preceding window represents a genuine
    breakout candidate.
    """

    highs = [100, 102, 101, 103, 99, 98, 97]

    candles = [
        create_candle(i + 1, Decimal(str(h)), high=Decimal(str(h)))
        for i, h in enumerate(highs)
    ]

    # Breakout day: close far above the recent range.
    candles.append(
        create_candle(8, Decimal("110"), high=Decimal("111"))
    )

    indicator = HighestHighIndicator(period=7)
    results = indicator.calculate(candles)

    # Only one result: day 8, window = days 1-7, max = 103
    assert len(results) == 1
    assert results[0].value == Decimal("103")
    assert results[0].trade_date == candles[-1].trade_date