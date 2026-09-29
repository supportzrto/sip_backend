from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.indicators.enums import IndicatorType


class IndicatorValue(BaseModel):
    """
    Base schema for all single-value indicators.
    """

    model_config = ConfigDict(frozen=True)

    symbol: str
    trade_date: date
    indicator: IndicatorType
    period: int
    value: Decimal


class MACDValue(BaseModel):
    """
    MACD calculation result.
    """

    model_config = ConfigDict(frozen=True)

    symbol: str
    trade_date: date
    indicator: IndicatorType

    fast_period: int
    slow_period: int
    signal_period: int

    macd: Decimal
    signal: Decimal
    histogram: Decimal


class RSIValue(IndicatorValue):
    """
    Relative Strength Index.
    """
    pass


class ATRValue(IndicatorValue):
    """
    Average True Range.
    """
    pass


class ADXValue(IndicatorValue):
    """
    Average Directional Index.
    """
    pass


class BollingerBandsValue(BaseModel):
    """
    Bollinger Bands.
    """

    model_config = ConfigDict(frozen=True)

    symbol: str
    trade_date: date
    indicator: IndicatorType
    period: int

    upper: Decimal
    middle: Decimal
    lower: Decimal


class SupertrendValue(IndicatorValue):
    """
    Supertrend indicator.
    """

    multiplier: Decimal
    is_bullish: bool


class RawFieldValue(BaseModel):
    """
    A raw OHLCV field (CLOSE, VOLUME, etc.) passed through as a
    pseudo-indicator value, so price/volume can be referenced
    directly in scan conditions via the same feature-store pipeline
    used by computed indicators.
    """

    model_config = ConfigDict(frozen=True)

    symbol: str
    trade_date: date
    field: str
    value: Decimal