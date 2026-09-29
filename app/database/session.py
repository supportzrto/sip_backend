from collections.abc import Generator

from sqlalchemy.orm import Session, sessionmaker

from app.database.engine import engine

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI database dependency.
    """
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()