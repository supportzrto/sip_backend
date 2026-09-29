from datetime import date, timedelta
from decimal import Decimal

from app.market_data.schemas import HistoricalCandle


def create_candle(
    day: int,
    close: Decimal,
    symbol: str = "TEST",
    open: Decimal | None = None,
    high: Decimal | None = None,
    low: Decimal | None = None,
    volume: int = 1000,
) -> HistoricalCandle:
    """
    Factory for creating HistoricalCandle objects in tests.
    """

    if open is None:
        open = close

    if high is None:
        high = close

    if low is None:
        low = close

    trade_date = date(2024, 1, 1) + timedelta(days=day - 1)

    return HistoricalCandle(
        symbol=symbol,
        trade_date=trade_date,
        open=open,
        high=high,
        low=low,
        close=close,
        volume=volume,
    )