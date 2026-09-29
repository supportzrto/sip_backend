from app.repositories.feature_definition_repository import (
    FeatureDefinitionRepository,
)

from app.scanner.enums import IndicatorField


class FeatureIdCache:
    """
    In-memory mapping between feature
    names and database IDs.
    """

    def __init__(
        self,
        repository: FeatureDefinitionRepository,
    ):
        self._repository = repository
        self._cache: dict[str, int] = {}

        self.refresh()

    def refresh(
        self,
    ) -> None:

        self._cache.clear()

        for feature in self._repository.list_all():

            self._cache[
                feature.name
            ] = feature.id

    def get_id(
        self,
        feature_name: str,
    ) -> int:

        return self._cache[feature_name]

    def exists(
        self,
        feature_name: str,
    ) -> bool:

        return feature_name in self._cache

    def size(
        self,
    ) -> int:

        return len(self._cache)

    def names(
        self,
    ) -> list[str]:

        return sorted(
            self._cache.keys()
        )
    


class FeatureNameCache:
    """
    In-memory mapping between feature
    IDs and IndicatorField values.
    """

    def __init__(
        self,
        repository: FeatureDefinitionRepository,
    ):
        self._repository = repository
        self._cache: dict[int, IndicatorField] = {}

        self.refresh()

    def refresh(
        self,
    ) -> None:

        self._cache.clear()

        for feature in self._repository.list_all():

            try:
                field = IndicatorField(feature.name)
            except ValueError:
                print(
                    f"Missing IndicatorField enum: {feature.name}"
                )
                continue

            self._cache[
                feature.id
            ] = field

    def get_name(
        self,
        feature_id: int,
    ) -> IndicatorField:

        return self._cache[feature_id]

    def exists(
        self,
        feature_id: int,
    ) -> bool:

        return feature_id in self._cache

    def size(
        self,
    ) -> int:

        return len(self._cache)

    def ids(
        self,
    ) -> list[int]:

        return sorted(
            self._cache.keys()
        )