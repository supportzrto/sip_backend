from app.feature_store.feature import Feature
from app.feature_store.feature_category import FeatureCategory


class FeatureRegistry:
    """
    In-memory registry of every
    feature supported by the platform.
    """

    def __init__(self):

        self._features: dict[str, Feature] = {}

    def register(
        self,
        feature: Feature,
    ) -> None:

        self._features[
            feature.name
        ] = feature

    def get(
        self,
        name: str,
    ) -> Feature:

        return self._features[name]

    def exists(
        self,
        name: str,
    ) -> bool:

        return name in self._features

    def all(
        self,
    ) -> list[Feature]:

        return list(
            self._features.values()
        )

    def by_category(
        self,
        category: FeatureCategory,
    ) -> list[Feature]:

        return [

            feature

            for feature in self._features.values()

            if feature.category == category

        ]