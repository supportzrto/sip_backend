from enum import Enum


class ScanStrategy(str, Enum):
    SWING = "SWING"
    BREAKOUT = "BREAKOUT"
    MOMENTUM = "MOMENTUM"
    MEAN_REVERSION = "MEAN_REVERSION"