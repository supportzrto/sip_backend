from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.feature.definition import FeatureDefinition


class FeatureDefinitionRepository:
    """
    Repository for FeatureDefinition.
    """

    def __init__(self, session: Session):
        self.session = session

    def get_by_name(
        self,
        name: str,
    ) -> FeatureDefinition | None:

        statement = (
            select(FeatureDefinition)
            .where(FeatureDefinition.name == name)
        )

        return self.session.scalar(statement)

    def list_all(
        self,
    ) -> list[FeatureDefinition]:

        statement = select(FeatureDefinition)

        return list(
            self.session.scalars(statement)
        )

    def create(
        self,
        feature: FeatureDefinition,
    ) -> FeatureDefinition:

        self.session.add(feature)

        self.session.flush()

        return feature

    def delete(
        self,
        feature: FeatureDefinition,
    ) -> None:

        self.session.delete(feature)