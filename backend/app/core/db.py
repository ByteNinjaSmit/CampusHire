"""Async engine, session factory and the per-request session dependency."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core import side_effects
from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, pool_size=10, max_overflow=10, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


@asynccontextmanager
async def managed_session(session: AsyncSession) -> AsyncIterator[AsyncSession]:
    """Commit on success, rollback on error, then flush staged side effects.

    Side effects (websocket publishes, Celery tasks) are only dispatched after a successful commit.
    """
    try:
        yield session
        await session.commit()
    except BaseException:
        await session.rollback()
        side_effects.discard(session)
        raise
    await side_effects.flush(session)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        async with managed_session(session):
            yield session


# scope="function": commit happens before the response is sent, so a client that fires its next
# request right after receiving a 2xx always sees committed data, and commit errors become responses.
DB = Annotated[AsyncSession, Depends(get_db, scope="function")]
