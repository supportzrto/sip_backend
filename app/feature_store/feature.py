from dataclasses import dataclass


from app.feature_store.feature_category import FeatureCategory
from app.feature_store.feature_data_type import FeatureDataType
@dataclass(frozen=True, slots=True)
class Feature:
    """
    Represents one market feature.

    Examples

    EMA20

    RSI14

    MACD

    BB_UPPER
    """

    name: str

    category: FeatureCategory

    data_type: FeatureDataType

    description: str