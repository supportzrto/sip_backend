from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AlertRuleCreate(BaseModel):
    """
    Exactly one of strategy_key / saved_strategy_id must be given:
    strategy_key names a built-in strategy (validated against
    app.scanner.strategies.AVAILABLE_STRATEGIES), saved_strategy_id
    points at one of the caller's own custom strategies created via
    POST /strategies (validated for ownership).
    """

    name: str = Field(min_length=1, max_length=100)

    strategy_key: str | None = None

    saved_strategy_id: int | None = None

    # None scans the whole instrument universe, same as running the
    # strategy directly via /scanner. Set, it restricts matching to
    # just that watchlist's symbols.
    watchlist_id: int | None = None

    is_active: bool = True

    @model_validator(mode="after")
    def _exactly_one_strategy_source(self) -> "AlertRuleCreate":

        if (self.strategy_key is None) == (self.saved_strategy_id is None):
            raise ValueError(
                "Provide exactly one of strategy_key or "
                "saved_strategy_id, not both or neither."
            )

        return self


class AlertRuleUpdate(BaseModel):
    """
    All fields optional -- only the ones provided are changed.
    Switching an existing rule from a built-in strategy to a saved
    one (or vice versa) means providing the new source; the old one
    is cleared automatically so the rule never ends up pointing at
    both. There's no way to explicitly clear watchlist_id back to
    None via this schema (it can only be left unset or set to a new
    id); create a new rule if you need to widen scope back to the
    full universe.
    """

    name: str | None = Field(default=None, min_length=1, max_length=100)

    strategy_key: str | None = None

    saved_strategy_id: int | None = None

    watchlist_id: int | None = None

    is_active: bool | None = None


class AlertRuleResponse(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: int

    user_id: int

    name: str

    strategy_key: str | None

    saved_strategy_id: int | None

    watchlist_id: int | None

    is_active: bool

    created_at: datetime

    updated_at: datetime

    last_checked_at: datetime | None

    last_matched_symbols: list[str]


class AlertRuleListResponse(BaseModel):

    model_config = ConfigDict(frozen=True)

    alerts: list[AlertRuleResponse]


class AlertNotificationResponse(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: int

    alert_rule_id: int

    symbol: str

    reasons: list[str]

    notified_at: datetime


class AlertNotificationListResponse(BaseModel):

    model_config = ConfigDict(frozen=True)

    notifications: list[AlertNotificationResponse]