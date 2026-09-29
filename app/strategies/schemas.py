from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.scanner.schemas import ScanExpression


class SavedStrategyCreate(BaseModel):

    name: str = Field(min_length=1, max_length=100)

    expression: ScanExpression


class SavedStrategyUpdate(BaseModel):
    """
    Both fields optional -- only the ones provided are changed.
    """

    name: str | None = Field(default=None, min_length=1, max_length=100)

    expression: ScanExpression | None = None


class SavedStrategyResponse(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: int

    user_id: int

    name: str

    expression: ScanExpression

    created_at: datetime

    updated_at: datetime


class SavedStrategyListResponse(BaseModel):

    model_config = ConfigDict(frozen=True)

    strategies: list[SavedStrategyResponse]