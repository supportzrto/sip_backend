from decimal import Decimal

from app.feature_store.cache import FeatureIdCache
from app.indicators.schemas import (
    BollingerBandsValue,
    IndicatorValue,
    MACDValue,
    RawFieldValue,
    SupertrendValue,
)
from app.models.feature.value import FeatureValue


class FeatureValueMapper:
    """
    Maps calculated feature values
    into database FeatureValue objects.
    """

    def __init__(
        self,
        cache: FeatureIdCache,
    ):
        self.cache = cache

    def map(
        self,
        instrument_id: int,
        trade_date,
        values: dict[str, Decimal],
    ) -> list[FeatureValue]:

        result: list[FeatureValue] = []

        for name, value in values.items():

            result.append(

                FeatureValue(

                    instrument_id=instrument_id,

                    feature_definition_id=self.cache.get_id(name),

                    trade_date=trade_date,

                    decimal_value=value,

                )

            )

        return result

    def map_history(
        self,
        instrument_id: int,
        indicator_results: dict[str, list],
    ) -> list[FeatureValue]:
        """
        Maps complete indicator history into
        FeatureValue ORM objects.
        """

        rows: list[FeatureValue] = []

        feature_ids = self.cache._cache

        for values in indicator_results.values():

            for value in values:

                #
                # Standard indicators
                #

                if isinstance(value, IndicatorValue):

                    feature_name = (
                        f"{value.indicator.value}"
                        f"{value.period}"
                    )

                    rows.append(

                        FeatureValue(

                            instrument_id=instrument_id,

                            feature_definition_id=feature_ids[
                                feature_name
                            ],

                            trade_date=value.trade_date,

                            decimal_value=value.value,

                        )

                    )

                #
                # MACD
                #

                elif isinstance(value, MACDValue):

                    rows.extend(

                        [

                            FeatureValue(

                                instrument_id=instrument_id,

                                feature_definition_id=feature_ids[
                                    "MACD"
                                ],

                                trade_date=value.trade_date,

                                decimal_value=value.macd,

                            ),

                            FeatureValue(

                                instrument_id=instrument_id,

                                feature_definition_id=feature_ids[
                                    "MACD_SIGNAL"
                                ],

                                trade_date=value.trade_date,

                                decimal_value=value.signal,

                            ),

                            FeatureValue(

                                instrument_id=instrument_id,

                                feature_definition_id=feature_ids[
                                    "MACD_HISTOGRAM"
                                ],

                                trade_date=value.trade_date,

                                decimal_value=value.histogram,

                            ),

                        ]

                    )

                #
                # Bollinger Bands
                #

                elif isinstance(
                    value,
                    BollingerBandsValue,
                ):

                    rows.extend(

                        [

                            FeatureValue(

                                instrument_id=instrument_id,

                                feature_definition_id=feature_ids[
                                    "BB_UPPER"
                                ],

                                trade_date=value.trade_date,

                                decimal_value=value.upper,

                            ),

                            FeatureValue(

                                instrument_id=instrument_id,

                                feature_definition_id=feature_ids[
                                    "BB_MIDDLE"
                                ],

                                trade_date=value.trade_date,

                                decimal_value=value.middle,

                            ),

                            FeatureValue(

                                instrument_id=instrument_id,

                                feature_definition_id=feature_ids[
                                    "BB_LOWER"
                                ],

                                trade_date=value.trade_date,

                                decimal_value=value.lower,

                            ),

                        ]

                    )

                #
                # Supertrend
                #

                elif isinstance(
                    value,
                    SupertrendValue,
                ):

                    rows.extend(

                        [

                            FeatureValue(

                                instrument_id=instrument_id,

                                feature_definition_id=feature_ids[
                                    f"SUPERTREND{value.period}"
                                ],

                                trade_date=value.trade_date,

                                decimal_value=value.value,

                            ),

                            FeatureValue(

                                instrument_id=instrument_id,

                                feature_definition_id=feature_ids[
                                    "SUPERTREND_BULLISH"
                                ],

                                trade_date=value.trade_date,

                                boolean_value=value.is_bullish,

                            ),

                        ]

                    )

                #
                # Raw market fields (OPEN/HIGH/LOW/CLOSE/VOLUME)
                #

                elif isinstance(value, RawFieldValue):

                    rows.append(

                        FeatureValue(

                            instrument_id=instrument_id,

                            feature_definition_id=feature_ids[
                                value.field
                            ],

                            trade_date=value.trade_date,

                            decimal_value=value.value,

                        )

                    )

        return rows