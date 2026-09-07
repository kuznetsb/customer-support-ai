from collections.abc import Iterator
from functools import cache

from settings import Settings
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


@cache
def get_session_factory(database_url: str) -> sessionmaker[Session]:
    """Return a cached SQLAlchemy session factory for a database URL."""
    engine = create_engine(database_url, pool_pre_ping=True)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session(settings: Settings | None = None) -> Iterator[Session]:
    """Yield a transactional session without creating database tables."""
    resolved_settings = settings or Settings()
    session = get_session_factory(resolved_settings.database.url)()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
