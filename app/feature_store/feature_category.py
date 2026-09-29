from enum import StrEnum


class FeatureCategory(StrEnum):
    """
    High-level grouping of market features.
    """

    PRICE = "PRICE"

    TREND = "TREND"

    MOMENTUM = "MOMENTUM"

    VOLATILITY = "VOLATILITY"

    TREND_STRENGTH = "TREND_STRENGTH"

    VOLUME = "VOLUME"

    PATTERN = "PATTERN"

    CUSTOM = "CUSTOM"