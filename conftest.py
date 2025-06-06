import asyncio
import pytest
from typing import AsyncGenerator, Generator

from fastapi import FastAPI 
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Import Base from your models to create tables in the test DB
from app.database import Base, get_db
from main import app as main_app # Import your FastAPI app instance

# Use a separate SQLite database for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_db.sqlite"

engine = create_async_engine(TEST_DATABASE_URL, echo=True)
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine, class_=AsyncSession
)
 
@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for each test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session", autouse=True)
async def setup_database() -> AsyncGenerator[None, None]:
    """Create tables before tests run and drop them after."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency override for get_db to use the test database."""
    async with TestingSessionLocal() as session:
        yield session

@pytest.fixture(scope="function") # Changed to function scope for cleaner tests
def app() -> FastAPI:
    main_app.dependency_overrides[get_db] = override_get_db
    return main_app

@pytest.fixture(scope="function") # Changed to function scope
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Create an AsyncClient for testing the FastAPI application."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
        