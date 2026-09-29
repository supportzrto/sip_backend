from datetime import datetime, date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class HistoricalInstrument(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str
    company_name: str
    exchange: str
    instrument_type: str

    isin: str | None = None

    provider: str

    provider_token: str | None = None

    is_active: bool = True


class HistoricalCandle(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str

    trade_date: date

    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal

    volume: int