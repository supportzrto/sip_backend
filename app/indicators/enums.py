from enum import Enum


class IndicatorType(str, Enum):
    """
    Supported technical indicators.
    """

    SMA = "SMA"

    EMA = "EMA"

    RSI = "RSI"

    MACD = "MACD"

    ATR = "ATR"

    BOLLINGER = "BOLLINGER"

    ADX = "ADX"

    SUPERTREND = "SUPERTREND"

    VWAP = "VWAP"

    STOCHASTIC = "STOCHASTIC"

    HIGHEST = "HIGHEST"

    LOWEST = "LOWEST"

    VOLUME_SURGE = "VOLUME_SURGE"

    # Raw market fields, passed through as pseudo-indicators so
    # they flow through the same feature-store pipeline as computed
    # indicators (needed for conditions like "CLOSE crosses above
    # the 252-day high").
    OPEN = "OPEN"

    HIGH = "HIGH"

    LOW = "LOW"

    CLOSE = "CLOSE"

    VOLUME = "VOLUME"