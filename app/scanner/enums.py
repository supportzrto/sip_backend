from enum import Enum


class ComparisonOperator(str, Enum):

    GREATER_THAN = ">"
    LESS_THAN = "<"

    GREATER_EQUAL = ">="
    LESS_EQUAL = "<="

    EQUAL = "=="
    NOT_EQUAL = "!="

    CROSSES_ABOVE = "crosses_above"
    CROSSES_BELOW = "crosses_below"


class LogicalOperator(str, Enum):

    AND = "AND"

    OR = "OR"

    NOT = "NOT"

class IndicatorField(str, Enum):

    CLOSE = "CLOSE"

    OPEN = "OPEN"

    HIGH = "HIGH"

    LOW = "LOW"

    VOLUME = "VOLUME"

    SMA20 = "SMA20"

    SMA50 = "SMA50"

    SMA200 = "SMA200"

    EMA20 = "EMA20"

    EMA50 = "EMA50"

    EMA200 = "EMA200"

    RSI14 = "RSI14"

    MACD = "MACD"

    MACD_SIGNAL = "MACD_SIGNAL"

    MACD_HISTOGRAM = "MACD_HISTOGRAM"

    ATR14 = "ATR14"

    ADX14 = "ADX14"

    SUPERTREND10 = "SUPERTREND10"

    SUPERTREND_BULLISH = "SUPERTREND_BULLISH"

    BB_UPPER = "BB_UPPER"

    BB_MIDDLE = "BB_MIDDLE"

    BB_LOWER = "BB_LOWER"

    HIGHEST252 = "HIGHEST252"

    LOWEST252 = "LOWEST252"

    VOLUME_SURGE20 = "VOLUME_SURGE20"