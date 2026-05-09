from __future__ import annotations

from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from httpx import AsyncClient
from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import verify_password
from app.dependencies import get_current_user
from app.models.user import Tenant, User
from conftest import (
    TEST_TENANT_ID,
    TEST_USER_EMAIL,
    TEST_USER_PASSWORD,
    create_test_token,
    register_user,
)


@pytest.mark.asyncio
async def test_register_new_user_returns_201(
    client: AsyncClient,
    test_tenant: Tenant,
) -> None:
    response = await register_user(client=client, tenant_id=test_tenant.id)

    assert response.status_code == 201
    data = response.json()
    assert UUID(data["id"])
    assert data["email"] == TEST_USER_EMAIL
    assert data["tenant_id"] == str(test_tenant.id)
    assert data["is_active"] is True
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_register_duplicate_email_returns_400(
    client: AsyncClient,
    test_tenant: Tenant,
) -> None:
    await register_user(client=client, tenant_id=test_tenant.id)

    response = await register_user(client=client, tenant_id=test_tenant.id)

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_register_invalid_email_format_returns_422(
    client: AsyncClient,
    test_tenant: Tenant,
) -> None:
    response = await register_user(
        client=client,
        email="not-an-email",
        tenant_id=test_tenant.id,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_missing_password_returns_422(
    client: AsyncClient,
    test_tenant: Tenant,
) -> None:
    response = await client.post(
        "/auth/register",
        json={
            "email": TEST_USER_EMAIL,
            "tenant_id": str(test_tenant.id),
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_invalid_tenant_id_returns_400(
    client: AsyncClient,
    test_tenant: Tenant,
) -> None:
    del test_tenant

    response = await register_user(client=client, tenant_id=uuid4())

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_register_stores_hashed_password_not_plaintext(
    client: AsyncClient,
    db_session: AsyncSession,
    test_tenant: Tenant,
) -> None:
    response = await register_user(client=client, tenant_id=test_tenant.id)

    assert response.status_code == 201
    user = await db_session.scalar(select(User).where(User.email == TEST_USER_EMAIL))
    assert user is not None
    assert user.hashed_password != TEST_USER_PASSWORD
    assert verify_password(TEST_USER_PASSWORD, user.hashed_password) is True


@pytest.mark.asyncio
async def test_login_valid_credentials_returns_token(
    client: AsyncClient,
    test_tenant: Tenant,
) -> None:
    await register_user(client=client, tenant_id=test_tenant.id)

    response = await client.post(
        "/auth/login",
        json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["access_token"]
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password_returns_401(
    client: AsyncClient,
    test_tenant: Tenant,
) -> None:
    await register_user(client=client, tenant_id=test_tenant.id)

    response = await client.post(
        "/auth/login",
        json={"email": TEST_USER_EMAIL, "password": "WrongPass123"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_email_returns_401(client: AsyncClient) -> None:
    response = await client.post(
        "/auth/login",
        json={"email": "missing@example.com", "password": TEST_USER_PASSWORD},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_token_contains_user_id_and_tenant_id(
    client: AsyncClient,
    test_tenant: Tenant,
) -> None:
    await register_user(client=client, tenant_id=test_tenant.id)

    response = await client.post(
        "/auth/login",
        json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
    )

    decoded_token = jwt.decode(
        response.json()["access_token"],
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )
    assert UUID(decoded_token["sub"])
    assert decoded_token["tenant_id"] == str(TEST_TENANT_ID)


@pytest.mark.asyncio
async def test_login_token_is_valid_jwt(
    client: AsyncClient,
    test_tenant: Tenant,
) -> None:
    await register_user(client=client, tenant_id=test_tenant.id)

    response = await client.post(
        "/auth/login",
        json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
    )

    decoded_token = jwt.decode(
        response.json()["access_token"],
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )
    assert decoded_token["sub"]
    assert decoded_token["tenant_id"]
    assert decoded_token["exp"]


@pytest.mark.asyncio
async def test_me_with_valid_token_returns_user_data(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    response = await client.get("/auth/me", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == TEST_USER_EMAIL
    assert data["tenant_id"] == str(TEST_TENANT_ID)


@pytest.mark.asyncio
async def test_me_without_token_returns_401(client: AsyncClient) -> None:
    response = await client.get("/auth/me")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_with_expired_token_returns_401(
    client: AsyncClient,
    db_session: AsyncSession,
    test_tenant: Tenant,
) -> None:
    user = User(
        tenant_id=test_tenant.id,
        email=TEST_USER_EMAIL,
        hashed_password="hashed",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    token = create_test_token(
        user_id=user.id,
        tenant_id=test_tenant.id,
        expires_delta=timedelta(minutes=-1),
    )

    response = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_with_malformed_token_returns_401(client: AsyncClient) -> None:
    response = await client.get(
        "/auth/me",
        headers={"Authorization": "Bearer malformed-token"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_returns_correct_tenant_id(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    response = await client.get("/auth/me", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["tenant_id"] == str(TEST_TENANT_ID)


@pytest.mark.asyncio
async def test_get_current_user_extracts_user_id_from_token() -> None:
    user_id = uuid4()
    token = create_test_token(user_id=user_id, tenant_id=TEST_TENANT_ID)

    auth_context = await get_current_user(
        HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    )

    assert auth_context["user_id"] == user_id


@pytest.mark.asyncio
async def test_get_current_user_extracts_tenant_id_from_token() -> None:
    user_id = uuid4()
    token = create_test_token(user_id=user_id, tenant_id=TEST_TENANT_ID)

    auth_context = await get_current_user(
        HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    )

    assert auth_context["tenant_id"] == TEST_TENANT_ID


@pytest.mark.asyncio
async def test_get_current_user_raises_401_on_invalid_token() -> None:
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(
            HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid-token")
        )

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_health_returns_ok(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
