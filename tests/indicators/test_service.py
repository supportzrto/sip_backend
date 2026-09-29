from app.indicators.service import IndicatorService
from tests.helpers.candle_factory import create_candle
from decimal import Decimal


def test_service_exists():

    service = IndicatorService()

    assert service.registry is not None


def test_calculate_all_returns_dict():

    candles = []

    for day in range(1, 250):

        candles.append(
            create_candle(
                day,
                Decimal(day),
            )
        )

    service = IndicatorService()

    results = service.calculate_all(
        candles
    )

    assert isinstance(
        results,
        dict,
    )


def test_contains_ema():

    candles = []

    for day in range(1, 250):

        candles.append(
            create_candle(
                day,
                Decimal(day),
            )
        )

    service = IndicatorService()

    results = service.calculate_all(
        candles
    )

    assert "EMA_20" in results


def test_contains_rsi():

    candles = []

    for day in range(1, 250):

        candles.append(
            create_candle(
                day,
                Decimal(day),
            )
        )

    service = IndicatorService()

    results = service.calculate_all(
        candles
    )

    assert "RSI_14" in results