from datetime import date
from decimal import Decimal

import pytest

from app.market_data.schemas import HistoricalCandle


@pytest.fixture
def create_candle():

    def _create_candle(
        day: int,
        close: Decimal,
    ) -> HistoricalCandle:

        return HistoricalCandle(
            symbol="TEST",
            trade_date=date(2024, 1, day),
            open=close,
            high=close,
            low=close,
            close=close,
            volume=1000,
        )

    return _create_candle