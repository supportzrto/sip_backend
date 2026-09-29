from fastapi import APIRouter, Depends, HTTPException

from app.alerts.schemas import (
    AlertNotificationListResponse,
    AlertNotificationResponse,
    AlertRuleCreate,
    AlertRuleListResponse,
    AlertRuleResponse,
    AlertRuleUpdate,
)
from app.api.dependencies.alerts import (
    get_alert_rule_repository,
    get_alert_service,
)
from app.api.dependencies.strategies import get_saved_strategy_repository
from app.api.dependencies.watchlists import get_watchlist_repository
from app.auth.dependencies import require_user
from app.models.alert_rule import AlertRule
from app.models.user import User
from app.repositories.alert_rule_repository import AlertRuleRepository
from app.repositories.saved_strategy_repository import (
    SavedStrategyRepository,
)
from app.repositories.watchlist_repository import WatchlistRepository
from app.scanner.schemas import ScanResult
from app.scanner.strategies import AVAILABLE_STRATEGIES
from app.services.alert_service import AlertService

router = APIRouter(
    prefix="/alerts",
    tags=["Alerts"],
    dependencies=[Depends(require_user)],
)


def _get_owned_rule_or_404(
    alert_rule_id: int,
    current_user: User,
    repository: AlertRuleRepository,
) -> AlertRule:

    alert_rule = repository.get_by_id(
        alert_rule_id,
        user_id=current_user.id,
    )

    if alert_rule is None:
        # 404, not 403 -- consistent with /scanner/runs and
        # /watchlists: don't reveal that a rule belonging to
        # someone else exists.
        raise HTTPException(
            status_code=404,
            detail="Alert rule not found.",
        )

    return alert_rule


def _validate_strategy_key(strategy_key: str) -> None:

    if strategy_key not in AVAILABLE_STRATEGIES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unknown strategy_key '{strategy_key}'. "
                f"See GET /scanner/strategies for available keys."
            ),
        )


def _validate_watchlist_ownership(
    watchlist_id: int | None,
    current_user: User,
    watchlist_repository: WatchlistRepository,
) -> None:

    if watchlist_id is None:
        return

    watchlist = watchlist_repository.get_by_id(
        watchlist_id,
        user_id=current_user.id,
    )

    if watchlist is None:
        raise HTTPException(
            status_code=404,
            detail="Watchlist not found.",
        )


def _validate_saved_strategy_ownership(
    saved_strategy_id: int,
    current_user: User,
    saved_strategy_repository: SavedStrategyRepository,
) -> None:

    saved_strategy = saved_strategy_repository.get_by_id(
        saved_strategy_id,
        user_id=current_user.id,
    )

    if saved_strategy is None:
        raise HTTPException(
            status_code=404,
            detail="Saved strategy not found.",
        )


@router.post("", status_code=201)
def create_alert_rule(
    request: AlertRuleCreate,
    current_user: User = Depends(require_user),
    repository: AlertRuleRepository = Depends(
        get_alert_rule_repository,
    ),
    watchlist_repository: WatchlistRepository = Depends(
        get_watchlist_repository,
    ),
    saved_strategy_repository: SavedStrategyRepository = Depends(
        get_saved_strategy_repository,
    ),
) -> AlertRuleResponse:

    if request.strategy_key is not None:
        _validate_strategy_key(request.strategy_key)
    else:
        _validate_saved_strategy_ownership(
            request.saved_strategy_id,
            current_user,
            saved_strategy_repository,
        )

    _validate_watchlist_ownership(
        request.watchlist_id, current_user, watchlist_repository,
    )

    alert_rule = repository.create(
        AlertRule(
            user_id=current_user.id,
            name=request.name,
            strategy_key=request.strategy_key,
            saved_strategy_id=request.saved_strategy_id,
            watchlist_id=request.watchlist_id,
            is_active=request.is_active,
        )
    )

    repository.commit()
    repository.db.refresh(alert_rule)

    return AlertRuleResponse.model_validate(alert_rule)


@router.get("")
def list_alert_rules(
    current_user: User = Depends(require_user),
    repository: AlertRuleRepository = Depends(
        get_alert_rule_repository,
    ),
) -> AlertRuleListResponse:

    alert_rules = repository.list_for_user(current_user.id)

    return AlertRuleListResponse(
        alerts=[
            AlertRuleResponse.model_validate(rule)
            for rule in alert_rules
        ],
    )


@router.get("/notifications/recent")
def list_recent_notifications(
    current_user: User = Depends(require_user),
    repository: AlertRuleRepository = Depends(
        get_alert_rule_repository,
    ),
) -> AlertNotificationListResponse:
    """
    The most recent alert notifications sent to the current user,
    across all of their rules -- newest first.
    """

    notifications = repository.list_recent_notifications_for_user(
        current_user.id,
    )

    return AlertNotificationListResponse(
        notifications=[
            AlertNotificationResponse.model_validate(n)
            for n in notifications
        ],
    )


@router.get("/{alert_rule_id}")
def get_alert_rule(
    alert_rule_id: int,
    current_user: User = Depends(require_user),
    repository: AlertRuleRepository = Depends(
        get_alert_rule_repository,
    ),
) -> AlertRuleResponse:

    alert_rule = _get_owned_rule_or_404(
        alert_rule_id, current_user, repository,
    )

    return AlertRuleResponse.model_validate(alert_rule)


@router.patch("/{alert_rule_id}")
def update_alert_rule(
    alert_rule_id: int,
    request: AlertRuleUpdate,
    current_user: User = Depends(require_user),
    repository: AlertRuleRepository = Depends(
        get_alert_rule_repository,
    ),
    watchlist_repository: WatchlistRepository = Depends(
        get_watchlist_repository,
    ),
    saved_strategy_repository: SavedStrategyRepository = Depends(
        get_saved_strategy_repository,
    ),
) -> AlertRuleResponse:

    alert_rule = _get_owned_rule_or_404(
        alert_rule_id, current_user, repository,
    )

    if request.strategy_key is not None and request.saved_strategy_id is not None:
        raise HTTPException(
            status_code=400,
            detail=(
                "Provide at most one of strategy_key or "
                "saved_strategy_id in a single update."
            ),
        )

    if request.name is not None:
        alert_rule.name = request.name

    if request.strategy_key is not None:
        # Switching to a built-in strategy clears any saved one, so
        # the rule never ends up satisfying neither/both of the
        # CHECK constraint's sides.
        _validate_strategy_key(request.strategy_key)
        alert_rule.strategy_key = request.strategy_key
        alert_rule.saved_strategy_id = None

    elif request.saved_strategy_id is not None:
        _validate_saved_strategy_ownership(
            request.saved_strategy_id,
            current_user,
            saved_strategy_repository,
        )
        alert_rule.saved_strategy_id = request.saved_strategy_id
        alert_rule.strategy_key = None

    if request.watchlist_id is not None:
        _validate_watchlist_ownership(
            request.watchlist_id, current_user, watchlist_repository,
        )
        alert_rule.watchlist_id = request.watchlist_id

    if request.is_active is not None:
        alert_rule.is_active = request.is_active

    repository.commit()
    repository.db.refresh(alert_rule)

    return AlertRuleResponse.model_validate(alert_rule)


@router.delete("/{alert_rule_id}", status_code=204)
def delete_alert_rule(
    alert_rule_id: int,
    current_user: User = Depends(require_user),
    repository: AlertRuleRepository = Depends(
        get_alert_rule_repository,
    ),
) -> None:

    alert_rule = _get_owned_rule_or_404(
        alert_rule_id, current_user, repository,
    )

    repository.delete(alert_rule)
    repository.commit()


@router.post("/{alert_rule_id}/run")
def run_alert_rule_now(
    alert_rule_id: int,
    current_user: User = Depends(require_user),
    repository: AlertRuleRepository = Depends(
        get_alert_rule_repository,
    ),
    service: AlertService = Depends(get_alert_service),
) -> list[ScanResult]:
    """
    Evaluate this rule immediately instead of waiting for the
    scheduler, and email any newly matched symbols right away.
    Useful right after creating a rule, to confirm it fires the way
    you expect without waiting for the next scheduled sync.
    """

    alert_rule = _get_owned_rule_or_404(
        alert_rule_id, current_user, repository,
    )

    return service.run_rule(alert_rule)