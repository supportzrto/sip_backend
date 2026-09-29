from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class FeatureValue:
    """
    Represents the value of one feature
    for one instrument on one trading day.
    """

    symbol: str

    trade_date: date

    feature_name: str

    value: Decimal | bool | int