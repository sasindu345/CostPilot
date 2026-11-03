"""Database access. Each transaction tells PostgreSQL who is asking, for Row-Level Security."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID

from sqlalchemy import URL, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

SET_CONTEXT = text(
    "SELECT set_config('app.user_id', :user_id, true), "
    "set_config('app.workspace_id', :workspace_id, true)"
)


async def set_context(
    session: AsyncSession, *, user_id: UUID | None = None, workspace_id: UUID | None = None
) -> None:
    """Applies to the current transaction only, so it cannot leak into the next request."""
    await session.execute(
        SET_CONTEXT,
        {"user_id": str(user_id or ""), "workspace_id": str(workspace_id or "")},
    )


class Database:
    def __init__(self, url: URL) -> None:
        self._engine = create_async_engine(url, pool_pre_ping=True)
        self._sessions = async_sessionmaker(self._engine, expire_on_commit=False)

    @asynccontextmanager
    async def transaction(
        self, *, user_id: UUID | None = None, workspace_id: UUID | None = None
    ) -> AsyncIterator[AsyncSession]:
        async with self._sessions() as session, session.begin():
            await set_context(session, user_id=user_id, workspace_id=workspace_id)
            yield session

    @property
    def engine(self) -> AsyncEngine:
        return self._engine

    async def close(self) -> None:
        await self._engine.dispose()
