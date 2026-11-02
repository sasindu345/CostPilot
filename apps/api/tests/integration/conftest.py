"""Creates the test database and brings it up to date before integration tests run."""

import asyncio
import subprocess  # nosec B404
import sys

import asyncpg
import pytest

from costpilot.shared.config import get_settings
from tests.conftest import TEST_DATABASE


async def create_database() -> None:
    settings = get_settings()
    connection = await asyncpg.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        user=settings.postgres_user,
        password=settings.postgres_password.get_secret_value(),
        database="postgres",
    )
    try:
        exists = await connection.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", TEST_DATABASE
        )
        if not exists:
            await connection.execute(f'CREATE DATABASE "{TEST_DATABASE}"')
    finally:
        await connection.close()


@pytest.fixture(scope="session", autouse=True)
def test_database() -> None:
    asyncio.run(create_database())
    subprocess.run(  # nosec B603
        [sys.executable, "-m", "alembic", "upgrade", "head"], check=True
    )
