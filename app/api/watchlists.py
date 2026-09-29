from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies.watchlists import (
    get_instrument_repository,
    get_watchlist_repository,
)
from app.auth.dependencies import require_user
from app.models.user import User
from app.models.watchlist import Watchlist
from app.models.watchlist_item import WatchlistItem
from app.repositories.instrument_repository import InstrumentRepository
from app.repositories.watchlist_repository import WatchlistRepository
from app.watchlists.schemas import (
    WatchlistCreate,
    WatchlistItemCreate,
    WatchlistItemResponse,
    WatchlistListResponse,
    WatchlistResponse,
)

router = APIRouter(
    prefix="/watchlists",
    tags=["Watchlists"],
    dependencies=[Depends(require_user)],
)


def _get_owned_watchlist_or_404(
    watchlist_id: int,
    current_user: User,
    repository: WatchlistRepository,
) -> Watchlist:

    watchlist = repository.get_by_id(
        watchlist_id,
        user_id=current_user.id,
    )

    if watchlist is None:
        # 404, not 403: a watchlist belonging to someone else
        # shouldn't be distinguishable from one that doesn't exist.
        raise HTTPException(
            status_code=404,
            detail="Watchlist not found.",
        )

    return watchlist


@router.post("", status_code=201)
def create_watchlist(
    request: WatchlistCreate,
    current_user: User = Depends(require_user),
    repository: WatchlistRepository = Depends(
        get_watchlist_repository,
    ),
) -> WatchlistResponse:

    existing = repository.list_for_user(current_user.id)

    if any(w.name == request.name for w in existing):
        raise HTTPException(
            status_code=409,
            detail=f"You already have a watchlist named '{request.name}'.",
        )

    watchlist = repository.create(
        Watchlist(
            user_id=current_user.id,
            name=request.name,
        )
    )

    repository.commit()
    repository.db.refresh(watchlist)

    return WatchlistResponse.model_validate(watchlist)


@router.get("")
def list_watchlists(
    current_user: User = Depends(require_user),
    repository: WatchlistRepository = Depends(
        get_watchlist_repository,
    ),
) -> WatchlistListResponse:

    watchlists = repository.list_for_user(current_user.id)

    return WatchlistListResponse(
        watchlists=[
            WatchlistResponse.model_validate(w) for w in watchlists
        ],
    )


@router.get("/{watchlist_id}")
def get_watchlist(
    watchlist_id: int,
    current_user: User = Depends(require_user),
    repository: WatchlistRepository = Depends(
        get_watchlist_repository,
    ),
) -> WatchlistResponse:

    watchlist = _get_owned_watchlist_or_404(
        watchlist_id, current_user, repository,
    )

    return WatchlistResponse.model_validate(watchlist)


@router.delete("/{watchlist_id}", status_code=204)
def delete_watchlist(
    watchlist_id: int,
    current_user: User = Depends(require_user),
    repository: WatchlistRepository = Depends(
        get_watchlist_repository,
    ),
) -> None:

    watchlist = _get_owned_watchlist_or_404(
        watchlist_id, current_user, repository,
    )

    repository.delete(watchlist)
    repository.commit()


@router.post("/{watchlist_id}/items", status_code=201)
def add_watchlist_item(
    watchlist_id: int,
    request: WatchlistItemCreate,
    current_user: User = Depends(require_user),
    repository: WatchlistRepository = Depends(
        get_watchlist_repository,
    ),
    instrument_repository: InstrumentRepository = Depends(
        get_instrument_repository,
    ),
) -> WatchlistItemResponse:

    watchlist = _get_owned_watchlist_or_404(
        watchlist_id, current_user, repository,
    )

    instrument = instrument_repository.get_by_symbol(
        request.symbol.upper(),
    )

    if instrument is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No instrument found for symbol "
                f"'{request.symbol}'."
            ),
        )

    if repository.get_item(watchlist.id, instrument.id) is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                f"'{instrument.symbol}' is already on this watchlist."
            ),
        )

    item = repository.add_item(
        WatchlistItem(
            watchlist_id=watchlist.id,
            instrument_id=instrument.id,
        )
    )

    repository.commit()
    repository.db.refresh(item)

    return WatchlistItemResponse.model_validate(item)


@router.delete(
    "/{watchlist_id}/items/{item_id}",
    status_code=204,
)
def remove_watchlist_item(
    watchlist_id: int,
    item_id: int,
    current_user: User = Depends(require_user),
    repository: WatchlistRepository = Depends(
        get_watchlist_repository,
    ),
) -> None:

    watchlist = _get_owned_watchlist_or_404(
        watchlist_id, current_user, repository,
    )

    item = next(
        (i for i in watchlist.items if i.id == item_id),
        None,
    )

    if item is None:
        raise HTTPException(
            status_code=404,
            detail="Watchlist item not found.",
        )

    repository.remove_item(item)
    repository.commit()