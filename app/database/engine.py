from sqlalchemy import create_engine

from app.config.settings import settings


def _normalize_database_url(url: str) -> str:
    """
    requirements.txt installs psycopg (v3), not psycopg2. SQLAlchemy
    defaults a bare 'postgresql://' URL to the psycopg2 dialect,
    which then fails with ModuleNotFoundError unless psycopg2 also
    happens to be installed. Force the v3 driver explicitly so
    DATABASE_URL works as written in .env.example without requiring
    people to know this.
    """

    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)

    return url


engine = create_engine(
    _normalize_database_url(settings.DATABASE_URL),
    echo=False,
    pool_pre_ping=True,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_recycle=1800,
)