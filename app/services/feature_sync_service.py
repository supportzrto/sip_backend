from sqlalchemy.orm import Session

from app.feature_store.generator import FeatureGenerator
from app.models.feature.definition import FeatureDefinition
from app.repositories.feature_definition_repository import (
    FeatureDefinitionRepository,
)


class FeatureSyncService:
    """
    Synchronizes all generated features
    into the database.
    """

    def __init__(
        self,
        session: Session,
    ):

        self.session = session

        self.repository = (
            FeatureDefinitionRepository(session)
        )

        self.generator = FeatureGenerator()

    def sync(self) -> None:

        registry = self.generator.generate()

        for feature in registry.all():

            existing = self.repository.get_by_name(
                feature.name
            )

            if existing is None:

                self.repository.create(

                    FeatureDefinition(

                        name=feature.name,

                        category=feature.category.value,

                        data_type=feature.data_type.value,

                        description=feature.description,

                    )

                )

        self.session.commit()