from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies.scanner import get_scanner_service
from app.api.dependencies.strategies import get_saved_strategy_repository
from app.auth.dependencies import require_user
from app.models.saved_strategy import SavedStrategy
from app.models.user import User
from app.repositories.saved_strategy_repository import (
    SavedStrategyRepository,
)
from app.scanner.schemas import ScanExpression, ScanRequest, ScanResult
from app.services.scanner_service import ScannerService
from app.strategies.schemas import (
    SavedStrategyCreate,
    SavedStrategyListResponse,
    SavedStrategyResponse,
    SavedStrategyUpdate,
)

router = APIRouter(
    prefix="/strategies",
    tags=["Saved Strategies"],
    dependencies=[Depends(require_user)],
)


def _get_owned_strategy_or_404(
    saved_strategy_id: int,
    current_user: User,
    repository: SavedStrategyRepository,
) -> SavedStrategy:

    saved_strategy = repository.get_by_id(
        saved_strategy_id,
        user_id=current_user.id,
    )

    if saved_strategy is None:
        # 404, not 403 -- same reasoning as /watchlists and
        # /scanner/runs: don't reveal that a strategy belonging to
        # someone else exists.
        raise HTTPException(
            status_code=404,
            detail="Saved strategy not found.",
        )

    return saved_strategy


@router.post("", status_code=201)
def create_saved_strategy(
    request: SavedStrategyCreate,
    current_user: User = Depends(require_user),
    repository: SavedStrategyRepository = Depends(
        get_saved_strategy_repository,
    ),
) -> SavedStrategyResponse:

    existing = repository.list_for_user(current_user.id)

    if any(s.name == request.name for s in existing):
        raise HTTPException(
            status_code=409,
            detail=(
                f"You already have a saved strategy named "
                f"'{request.name}'."
            ),
        )

    saved_strategy = repository.create(
        SavedStrategy(
            user_id=current_user.id,
            name=request.name,
            expression=request.expression.model_dump(mode="json"),
        )
    )

    repository.commit()
    repository.db.refresh(saved_strategy)

    return SavedStrategyResponse.model_validate(saved_strategy)


@router.get("")
def list_saved_strategies(
    current_user: User = Depends(require_user),
    repository: SavedStrategyRepository = Depends(
        get_saved_strategy_repository,
    ),
) -> SavedStrategyListResponse:

    strategies = repository.list_for_user(current_user.id)

    return SavedStrategyListResponse(
        strategies=[
            SavedStrategyResponse.model_validate(s) for s in strategies
        ],
    )


@router.get("/{saved_strategy_id}")
def get_saved_strategy(
    saved_strategy_id: int,
    current_user: User = Depends(require_user),
    repository: SavedStrategyRepository = Depends(
        get_saved_strategy_repository,
    ),
) -> SavedStrategyResponse:

    saved_strategy = _get_owned_strategy_or_404(
        saved_strategy_id, current_user, repository,
    )

    return SavedStrategyResponse.model_validate(saved_strategy)


@router.patch("/{saved_strategy_id}")
def update_saved_strategy(
    saved_strategy_id: int,
    request: SavedStrategyUpdate,
    current_user: User = Depends(require_user),
    repository: SavedStrategyRepository = Depends(
        get_saved_strategy_repository,
    ),
) -> SavedStrategyResponse:

    saved_strategy = _get_owned_strategy_or_404(
        saved_strategy_id, current_user, repository,
    )

    if request.name is not None:

        existing = repository.list_for_user(current_user.id)

        if any(
            s.name == request.name and s.id != saved_strategy.id
            for s in existing
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    f"You already have a saved strategy named "
                    f"'{request.name}'."
                ),
            )

        saved_strategy.name = request.name

    if request.expression is not None:
        saved_strategy.expression = request.expression.model_dump(
            mode="json",
        )

    repository.commit()
    repository.db.refresh(saved_strategy)

    return SavedStrategyResponse.model_validate(saved_strategy)


@router.delete("/{saved_strategy_id}", status_code=204)
def delete_saved_strategy(
    saved_strategy_id: int,
    current_user: User = Depends(require_user),
    repository: SavedStrategyRepository = Depends(
        get_saved_strategy_repository,
    ),
) -> None:
    """
    Deleting a saved strategy also deletes any alert rules built on
    top of it (ON DELETE CASCADE) -- unlike a watchlist, which an
    alert rule survives losing (see AlertRule.watchlist_id), a rule
    has nothing left to scan for once its strategy is gone.
    """

    saved_strategy = _get_owned_strategy_or_404(
        saved_strategy_id, current_user, repository,
    )

    repository.delete(saved_strategy)
    repository.commit()


@router.post("/{saved_strategy_id}/scan")
def run_saved_strategy(
    saved_strategy_id: int,
    current_user: User = Depends(require_user),
    repository: SavedStrategyRepository = Depends(
        get_saved_strategy_repository,
    ),
    service: ScannerService = Depends(get_scanner_service),
) -> list[ScanResult]:
    """
    Run a saved strategy immediately, the same way
    POST /scanner/strategies/{key}/scan runs a built-in one.
    """

    saved_strategy = _get_owned_strategy_or_404(
        saved_strategy_id, current_user, repository,
    )

    request = ScanRequest(
        strategy_name=saved_strategy.name,
        expression=ScanExpression.model_validate(
            saved_strategy.expression,
        ),
    )

    return service.scan(request, user_id=current_user.id)