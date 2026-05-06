from collections.abc import AsyncIterator
from uuid import UUID

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base, get_db_session
from app.main import app
from app.models.user import Tenant


TEST_TENANT_ID = UUID("11111111-1111-1111-1111-111111111111")


@pytest_asyncio.fixture()
async def client() -> AsyncIterator[AsyncClient]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with testing_session() as session:
        session.add(Tenant(id=TEST_TENANT_ID, name="TDSE Test Tenant"))
        await session.commit()

    async def override_get_db_session() -> AsyncIterator[AsyncSession]:
        async with testing_session() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as async_client:
        yield async_client

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_register_user(client: AsyncClient) -> None:
    response = await client.post(
        "/auth/register",
        json={
            "email": "student@example.com",
            "password": "StrongPass123",
            "tenant_id": str(TEST_TENANT_ID),
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "student@example.com"
    assert data["tenant_id"] == str(TEST_TENANT_ID)
    assert data["is_active"] is True
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_login_returns_jwt_with_tenant_id(client: AsyncClient) -> None:
    await client.post(
        "/auth/register",
        json={
            "email": "clinician@example.com",
            "password": "StrongPass123",
            "tenant_id": str(TEST_TENANT_ID),
        },
    )

    response = await client.post(
        "/auth/login",
        json={
            "email": "clinician@example.com",
            "password": "StrongPass123",
        },
    )

    assert response.status_code == 200
    data = response.json()
    decoded_token = jwt.decode(
        data["access_token"],
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )
    assert data["token_type"] == "bearer"
    assert decoded_token["tenant_id"] == str(TEST_TENANT_ID)
    assert decoded_token["sub"]


@pytest.mark.asyncio
async def test_invalid_token_is_rejected(client: AsyncClient) -> None:
    response = await client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
