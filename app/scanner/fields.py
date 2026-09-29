from enum import Enum


class IndicatorField(str, Enum):

    # Price
    OPEN = "OPEN"
    HIGH = "HIGH"
    LOW = "LOW"
    CLOSE = "CLOSE"
    VOLUME = "VOLUME"

    # SMA
    SMA20 = "SMA20"
    SMA50 = "SMA50"
    SMA200 = "SMA200"

    # EMA
    EMA20 = "EMA20"
    EMA50 = "EMA50"
    EMA200 = "EMA200"

    # RSI
    RSI14 = "RSI14"

    # ATR
    ATR14 = "ATR14"

    # ADX
    ADX14 = "ADX14"

    # MACD
    MACD = "MACD"
    MACD_SIGNAL = "MACD_SIGNAL"
    MACD_HISTOGRAM = "MACD_HISTOGRAM"

    # Bollinger
    BB_UPPER = "BB_UPPER"
    BB_MIDDLE = "BB_MIDDLE"
    BB_LOWER = "BB_LOWER"

    # Supertrend
    SUPERTREND10 = "SUPERTREND10"
    SUPERTREND_BULLISH = "SUPERTREND_BULLISH"