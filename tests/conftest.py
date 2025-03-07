import asyncio
from typing import AsyncGenerator
from typing import Generator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport
from httpx import AsyncClient

from tests.fastapi_app import app as fastapi_app


@pytest.fixture()
def app() -> FastAPI:
    return fastapi_app


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncGenerator:
    async with AsyncClient(
            transport=ASGITransport(app),
            base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture(scope="session")
def event_loop(request) -> Generator:
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
