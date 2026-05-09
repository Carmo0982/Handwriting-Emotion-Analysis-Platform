from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

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
TEST_USER_EMAIL = "clinician@example.com"
TEST_USER_PASSWORD = "StrongPass123"


@pytest_asyncio.fixture()
async def db_session() -> AsyncIterator[AsyncSession]:
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
        yield session

    await engine.dispose()


@pytest_asyncio.fixture()
async def test_tenant(db_session: AsyncSession) -> Tenant:
    tenant = Tenant(id=TEST_TENANT_ID, name="TDSE Test Tenant")
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    return tenant


@pytest_asyncio.fixture()
async def client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    async def override_get_db_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db_session
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as async_client:
        yield async_client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture()
async def auth_headers(client: AsyncClient, test_tenant: Tenant) -> dict[str, str]:
    await register_user(
        client=client,
        email=TEST_USER_EMAIL,
        password=TEST_USER_PASSWORD,
        tenant_id=test_tenant.id,
    )
    response = await client.post(
        "/auth/login",
        json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def register_user(
    client: AsyncClient,
    email: str = TEST_USER_EMAIL,
    password: str = TEST_USER_PASSWORD,
    tenant_id: UUID = TEST_TENANT_ID,
) -> Any:
    return await client.post(
        "/auth/register",
        json={
            "email": email,
            "password": password,
            "tenant_id": str(tenant_id),
        },
    )


def create_test_token(
    user_id: UUID,
    tenant_id: UUID,
    expires_delta: timedelta = timedelta(minutes=15),
) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": str(user_id),
            "tenant_id": str(tenant_id),
            "iat": now,
            "exp": now + expires_delta,
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
