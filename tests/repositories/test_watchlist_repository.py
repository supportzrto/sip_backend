from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.models.instrument import Instrument
from app.models.user import User
from app.models.watchlist import Watchlist
from app.models.watchlist_item import WatchlistItem
from app.repositories.watchlist_repository import WatchlistRepository


def create_session():

    engine = create_engine("sqlite:///:memory:")

    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)

    return Session()


def create_user(session, email="jane@example.com"):

    user = User(
        full_name="Jane Doe",
        email=email,
        password_hash="not-a-real-hash",
    )

    session.add(user)
    session.commit()

    return user


def create_instrument(session, symbol="RELIANCE"):

    instrument = Instrument(
        symbol=symbol,
        company_name=f"{symbol} Ltd",
        exchange="NSE",
        instrument_type="EQ",
        isin=f"INE{symbol}01018"[:12],
        provider="NSE",
        provider_token=symbol,
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    session.add(instrument)
    session.commit()

    return instrument


def test_create_and_list_for_user():

    session = create_session()
    user = create_user(session)
    repository = WatchlistRepository(session)

    repository.create(Watchlist(user_id=user.id, name="My Longs"))
    repository.commit()

    watchlists = repository.list_for_user(user.id)

    assert len(watchlists) == 1
    assert watchlists[0].name == "My Longs"


def test_get_by_id_scoped_to_owner():

    session = create_session()
    owner = create_user(session, email="owner@example.com")
    other = create_user(session, email="other@example.com")
    repository = WatchlistRepository(session)

    watchlist = repository.create(
        Watchlist(user_id=owner.id, name="My Longs"),
    )
    repository.commit()

    # Owner can fetch it.
    assert repository.get_by_id(watchlist.id, user_id=owner.id) is not None

    # A different user cannot.
    assert repository.get_by_id(watchlist.id, user_id=other.id) is None

    # No user_id scoping (internal/scheduler use) returns it either way.
    assert repository.get_by_id(watchlist.id) is not None


def test_add_item_and_get_symbols():

    session = create_session()
    user = create_user(session)
    instrument = create_instrument(session, symbol="RELIANCE")
    repository = WatchlistRepository(session)

    watchlist = repository.create(
        Watchlist(user_id=user.id, name="My Longs"),
    )
    repository.commit()

    repository.add_item(
        WatchlistItem(
            watchlist_id=watchlist.id,
            instrument_id=instrument.id,
        )
    )
    repository.commit()

    assert repository.get_symbols(watchlist.id) == ["RELIANCE"]


def test_add_item_is_idempotent_checked_via_get_item():

    session = create_session()
    user = create_user(session)
    instrument = create_instrument(session, symbol="RELIANCE")
    repository = WatchlistRepository(session)

    watchlist = repository.create(
        Watchlist(user_id=user.id, name="My Longs"),
    )
    repository.commit()

    repository.add_item(
        WatchlistItem(
            watchlist_id=watchlist.id,
            instrument_id=instrument.id,
        )
    )
    repository.commit()

    # A caller is expected to check get_item() before adding again
    # (this is exactly what the API route does) -- confirm the
    # lookup that guard depends on actually finds the existing row.
    assert repository.get_item(watchlist.id, instrument.id) is not None

    # And that the DB-level uniqueness constraint is really there as
    # a backstop, in case a caller skips that check.
    with pytest.raises(IntegrityError):
        repository.add_item(
            WatchlistItem(
                watchlist_id=watchlist.id,
                instrument_id=instrument.id,
            )
        )


def test_delete_watchlist_cascades_to_items():

    session = create_session()
    user = create_user(session)
    instrument = create_instrument(session, symbol="RELIANCE")
    repository = WatchlistRepository(session)

    watchlist = repository.create(
        Watchlist(user_id=user.id, name="My Longs"),
    )
    repository.commit()

    repository.add_item(
        WatchlistItem(
            watchlist_id=watchlist.id,
            instrument_id=instrument.id,
        )
    )
    repository.commit()

    repository.delete(watchlist)
    repository.commit()

    assert repository.list_for_user(user.id) == []