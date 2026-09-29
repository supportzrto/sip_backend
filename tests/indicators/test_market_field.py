from decimal import Decimal

from app.indicators.enums import IndicatorType
from app.indicators.market_field import MarketFieldIndicator
from app.indicators.schemas import RawFieldValue
from tests.helpers.candle_factory import create_candle


def test_extracts_close_price_per_candle():

    candles = [
        create_candle(1, Decimal("100")),
        create_candle(2, Decimal("105")),
    ]

    indicator = MarketFieldIndicator(
        IndicatorType.CLOSE,
        lambda c: c.close,
    )

    results = indicator.calculate(candles)

    assert len(results) == 2
    assert all(isinstance(r, RawFieldValue) for r in results)
    assert results[0].value == Decimal("100")
    assert results[0].field == "CLOSE"
    assert results[1].value == Decimal("105")


def test_extracts_volume():

    candles = [create_candle(1, Decimal("100"), volume=5000)]

    indicator = MarketFieldIndicator(
        IndicatorType.VOLUME,
        lambda c: c.volume,
    )

    results = indicator.calculate(candles)

    assert results[0].value == Decimal("5000")
    assert results[0].field == "VOLUME"


def test_empty_candles_returns_empty():

    indicator = MarketFieldIndicator(IndicatorType.CLOSE, lambda c: c.close)

    assert indicator.calculate([]) == []