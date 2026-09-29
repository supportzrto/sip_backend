from app.feature_store.feature import Feature
from app.feature_store.feature_category import FeatureCategory
from app.feature_store.feature_data_type import FeatureDataType
from app.feature_store.registry import FeatureRegistry

from app.indicators.enums import IndicatorType
from app.indicators.registry import IndicatorRegistry


class FeatureGenerator:
    """
    Generates all platform features from the
    registered indicators.

    Standard indicators (EMA, SMA, RSI, ATR, ADX)
    are generated automatically.

    Composite indicators (MACD, Bollinger,
    Supertrend) and market fields are registered
    separately.
    """

    def __init__(
        self,
        indicator_registry: IndicatorRegistry | None = None,
    ):

        self.indicator_registry = (
            indicator_registry
            or IndicatorRegistry()
        )

    def generate(
        self,
    ) -> FeatureRegistry:
        """
        Generate every supported feature.
        """

        registry = FeatureRegistry()

        for indicator in self.indicator_registry.indicators:

            self._register_indicator(
                registry,
                indicator,
            )

        self._register_special_features(
            registry,
        )

        return registry

    def _register_indicator(
        self,
        registry: FeatureRegistry,
        indicator,
    ) -> None:
        """
        Register one standard indicator.
        """

        indicator_type = indicator.indicator_type

        if indicator_type == IndicatorType.SMA:

            self._register_period_feature(
                registry,
                prefix="SMA",
                period=indicator.period,
                category=FeatureCategory.TREND,
            )

        elif indicator_type == IndicatorType.EMA:

            self._register_period_feature(
                registry,
                prefix="EMA",
                period=indicator.period,
                category=FeatureCategory.TREND,
            )

        elif indicator_type == IndicatorType.RSI:

            self._register_period_feature(
                registry,
                prefix="RSI",
                period=indicator.period,
                category=FeatureCategory.MOMENTUM,
            )

        elif indicator_type == IndicatorType.ATR:

            self._register_period_feature(
                registry,
                prefix="ATR",
                period=indicator.period,
                category=FeatureCategory.VOLATILITY,
            )

        elif indicator_type == IndicatorType.ADX:

            self._register_period_feature(
                registry,
                prefix="ADX",
                period=indicator.period,
                category=FeatureCategory.TREND_STRENGTH,
            )

        elif indicator_type == IndicatorType.HIGHEST:

            self._register_period_feature(
                registry,
                prefix="HIGHEST",
                period=indicator.period,
                category=FeatureCategory.PRICE,
            )

        elif indicator_type == IndicatorType.LOWEST:

            self._register_period_feature(
                registry,
                prefix="LOWEST",
                period=indicator.period,
                category=FeatureCategory.PRICE,
            )

        elif indicator_type == IndicatorType.VOLUME_SURGE:

            self._register_period_feature(
                registry,
                prefix="VOLUME_SURGE",
                period=indicator.period,
                category=FeatureCategory.VOLUME,
            )

    def _register_period_feature(
        self,
        registry: FeatureRegistry,
        prefix: str,
        period: int,
        category: FeatureCategory,
    ) -> None:
        """
        Register a standard period-based feature.
        """

        registry.register(
            Feature(
                name=f"{prefix}{period}",
                category=category,
                data_type=FeatureDataType.DECIMAL,
                description=f"{period}-period {prefix}",
            )
        )

    def _register_special_features(
        self,
        registry: FeatureRegistry,
    ) -> None:
        """
        Register composite indicators and
        market fields.
        """

        #
        # MACD
        #

        registry.register(
            Feature(
                name="MACD",
                category=FeatureCategory.MOMENTUM,
                data_type=FeatureDataType.DECIMAL,
                description="MACD Line",
            )
        )

        registry.register(
            Feature(
                name="MACD_SIGNAL",
                category=FeatureCategory.MOMENTUM,
                data_type=FeatureDataType.DECIMAL,
                description="MACD Signal Line",
            )
        )

        registry.register(
            Feature(
                name="MACD_HISTOGRAM",
                category=FeatureCategory.MOMENTUM,
                data_type=FeatureDataType.DECIMAL,
                description="MACD Histogram",
            )
        )

        #
        # Bollinger Bands
        #

        registry.register(
            Feature(
                name="BB_UPPER",
                category=FeatureCategory.VOLATILITY,
                data_type=FeatureDataType.DECIMAL,
                description="Upper Bollinger Band",
            )
        )

        registry.register(
            Feature(
                name="BB_MIDDLE",
                category=FeatureCategory.VOLATILITY,
                data_type=FeatureDataType.DECIMAL,
                description="Middle Bollinger Band",
            )
        )

        registry.register(
            Feature(
                name="BB_LOWER",
                category=FeatureCategory.VOLATILITY,
                data_type=FeatureDataType.DECIMAL,
                description="Lower Bollinger Band",
            )
        )

        #
        # Supertrend
        #

        registry.register(
            Feature(
                name="SUPERTREND10",
                category=FeatureCategory.TREND,
                data_type=FeatureDataType.DECIMAL,
                description="Supertrend Value",
            )
        )

        registry.register(
            Feature(
                name="SUPERTREND_BULLISH",
                category=FeatureCategory.TREND,
                data_type=FeatureDataType.BOOLEAN,
                description="Supertrend Bullish Flag",
            )
        )

        #
        # Market Fields
        #

        registry.register(
            Feature(
                name="OPEN",
                category=FeatureCategory.PRICE,
                data_type=FeatureDataType.DECIMAL,
                description="Opening Price",
            )
        )

        registry.register(
            Feature(
                name="HIGH",
                category=FeatureCategory.PRICE,
                data_type=FeatureDataType.DECIMAL,
                description="High Price",
            )
        )

        registry.register(
            Feature(
                name="LOW",
                category=FeatureCategory.PRICE,
                data_type=FeatureDataType.DECIMAL,
                description="Low Price",
            )
        )

        registry.register(
            Feature(
                name="CLOSE",
                category=FeatureCategory.PRICE,
                data_type=FeatureDataType.DECIMAL,
                description="Closing Price",
            )
        )

        registry.register(
            Feature(
                name="VOLUME",
                category=FeatureCategory.VOLUME,
                data_type=FeatureDataType.INTEGER,
                description="Trading Volume",
            )
        )