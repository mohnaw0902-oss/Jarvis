from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from jarvis.database.session import create_schema, create_session_factory


@pytest.fixture
async def session_factory(tmp_path) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine, sessions = create_session_factory(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    await create_schema(engine)
    yield sessions
    await engine.dispose()
