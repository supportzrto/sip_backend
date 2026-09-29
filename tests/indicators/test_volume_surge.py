from decimal import Decimal

import pytest

from app.indicators.enums import IndicatorType
from app.indicators.volume_surge import VolumeSurgeIndicator
from tests.helpers.candle_factory import create_candle


def test_invalid_period():

    with pytest.raises(ValueError):
        VolumeSurgeIndicator(period=1)


def test_empty_candles():

    assert VolumeSurgeIndicator(period=5).calculate([]) == []


def test_not_enough_candles_returns_empty():

    candles = [
        create_candle(i, Decimal("100"), volume=1000)
        for i in range(1, 4)
    ]

    assert VolumeSurgeIndicator(period=5).calculate(candles) == []


def test_volume_surge_ratio_excludes_current_day():

    volumes = [1000, 1000, 1000, 1000, 1000]  # 5 days at baseline

    candles = [
        create_candle(i + 1, Decimal("100"), volume=v)
        for i, v in enumerate(volumes)
    ]

    # Day 6: a genuine volume surge -- 3x the recent average.
    candles.append(
        create_candle(6, Decimal("100"), volume=3000)
    )

    indicator = VolumeSurgeIndicator(period=5)
    results = indicator.calculate(candles)

    assert len(results) == 1
    assert results[0].value == Decimal("3.0000")
    assert results[0].indicator == IndicatorType.VOLUME_SURGE
    assert results[0].period == 5


def test_normal_volume_day_has_ratio_near_one():

    volumes = [1000, 1100, 900, 1000, 1000, 1050]

    candles = [
        create_candle(i + 1, Decimal("100"), volume=v)
        for i, v in enumerate(volumes)
    ]

    indicator = VolumeSurgeIndicator(period=5)
    results = indicator.calculate(candles)

    # window = first 5 volumes = [1000,1100,900,1000,1000] avg=1000
    # today's volume = 1050 -> ratio 1.05
    assert results[0].value == Decimal("1.0500")


def test_zero_average_volume_does_not_divide_by_zero():

    candles = [
        create_candle(i + 1, Decimal("100"), volume=0)
        for i in range(5)
    ]
    candles.append(create_candle(6, Decimal("100"), volume=500))

    indicator = VolumeSurgeIndicator(period=5)
    results = indicator.calculate(candles)

    assert results[0].value == Decimal("0")