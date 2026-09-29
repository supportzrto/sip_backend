from decimal import Decimal

from app.market.analyzer import MarketAnalyzer
from tests.helpers.candle_factory import create_candle


def test_market_analyzer():

    candles = []

    for day in range(1, 250):

        candles.append(
            create_candle(
                day,
                Decimal(day),
            )
        )

    analyzer = MarketAnalyzer()

    snapshot = analyzer.analyze(
        candles
    )

    assert snapshot.current.values

    assert snapshot.previous.values