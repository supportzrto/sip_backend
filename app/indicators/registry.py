from app.indicators.adx import ADXIndicator
from app.indicators.atr import ATRIndicator
from app.indicators.bollinger import BollingerBandsIndicator
from app.indicators.breakout_levels import (
    HighestHighIndicator,
    LowestLowIndicator,
)
from app.indicators.ema import EMAIndicator
from app.indicators.enums import IndicatorType
from app.indicators.macd import MACDIndicator
from app.indicators.market_field import MarketFieldIndicator
from app.indicators.rsi import RSIIndicator
from app.indicators.sma import SMAIndicator
from app.indicators.supertrend import SupertrendIndicator
from app.indicators.volume_surge import VolumeSurgeIndicator


class IndicatorRegistry:
    """
    Registry of all supported indicators.
    """

    def __init__(self):

        self._indicators = [

            SMAIndicator(20),
            SMAIndicator(50),

            EMAIndicator(20),
            EMAIndicator(50),
            EMAIndicator(200),

            RSIIndicator(14),

            ATRIndicator(14),

            ADXIndicator(14),

            BollingerBandsIndicator(20),

            MACDIndicator(),

            SupertrendIndicator(),

            HighestHighIndicator(252),
            LowestLowIndicator(252),

            VolumeSurgeIndicator(20),

            MarketFieldIndicator(IndicatorType.OPEN, lambda c: c.open),
            MarketFieldIndicator(IndicatorType.HIGH, lambda c: c.high),
            MarketFieldIndicator(IndicatorType.LOW, lambda c: c.low),
            MarketFieldIndicator(IndicatorType.CLOSE, lambda c: c.close),
            MarketFieldIndicator(IndicatorType.VOLUME, lambda c: c.volume),

        ]

    @property
    def indicators(self):
        return self._indicators