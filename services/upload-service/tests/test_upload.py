from collections.abc import AsyncIterator
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from jose import jwt

from app.core.config import settings
from app.main import app
from app.services.upload_service import clear_image_status_store


TEST_USER_ID = UUID("22222222-2222-2222-2222-222222222222")
TEST_TENANT_ID = UUID("11111111-1111-1111-1111-111111111111")


@pytest_asyncio.fixture(autouse=True)
async def reset_status_store() -> AsyncIterator[None]:
    clear_image_status_store()
    yield
    clear_image_status_store()


@pytest_asyncio.fixture()
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as async_client:
        yield async_client


def make_token(
    user_id: UUID = TEST_USER_ID,
    tenant_id: UUID = TEST_TENANT_ID,
) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": str(user_id),
            "tenant_id": str(tenant_id),
            "iat": now,
            "exp": now + timedelta(minutes=15),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_upload_image_to_s3_and_publish_kafka_event(
    client: AsyncClient,
) -> None:
    token = make_token()
    image_bytes = b"\x89PNG\r\n\x1a\nvalid-image-bytes"

    with patch(
        "app.services.upload_service.upload_to_s3",
        return_value="uploaded-key",
    ) as upload_mock, patch(
        "app.services.upload_service.publish_event",
        new_callable=AsyncMock,
    ) as publish_mock:
        response = await client.post(
            "/upload",
            headers=auth_headers(token),
            files={"file": ("sample.png", image_bytes, "image/png")},
        )

    assert response.status_code == 202
    data = response.json()
    image_id = UUID(data["image_id"])
    expected_key = f"{TEST_TENANT_ID}/{TEST_USER_ID}/{image_id}.png"

    assert data["status"] == "processing"
    upload_mock.assert_called_once_with(image_bytes, expected_key)
    publish_mock.assert_awaited_once()

    topic, payload = publish_mock.await_args.args
    assert topic == "image-uploaded"
    assert payload["image_id"] == str(image_id)
    assert payload["tenant_id"] == str(TEST_TENANT_ID)
    assert payload["user_id"] == str(TEST_USER_ID)
    assert payload["s3_key"] == "uploaded-key"
    assert "timestamp" in payload


@pytest.mark.asyncio
async def test_upload_rejects_unsupported_content_type(
    client: AsyncClient,
) -> None:
    token = make_token()

    with patch("app.services.upload_service.upload_to_s3") as upload_mock, patch(
        "app.services.upload_service.publish_event",
        new_callable=AsyncMock,
    ) as publish_mock:
        response = await client.post(
            "/upload",
            headers=auth_headers(token),
            files={"file": ("notes.txt", b"not-an-image", "text/plain")},
        )

    assert response.status_code == 415
    upload_mock.assert_not_called()
    publish_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_upload_rejects_files_larger_than_10mb(
    client: AsyncClient,
) -> None:
    token = make_token()
    oversized_file = b"x" * (settings.max_upload_size_bytes + 1)

    with patch("app.services.upload_service.upload_to_s3") as upload_mock, patch(
        "app.services.upload_service.publish_event",
        new_callable=AsyncMock,
    ) as publish_mock:
        response = await client.post(
            "/upload",
            headers=auth_headers(token),
            files={"file": ("sample.png", oversized_file, "image/png")},
        )

    assert response.status_code == 413
    upload_mock.assert_not_called()
    publish_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_upload_status_returns_processing(
    client: AsyncClient,
) -> None:
    token = make_token()

    with patch(
        "app.services.upload_service.upload_to_s3",
        return_value="uploaded-key",
    ), patch(
        "app.services.upload_service.publish_event",
        new_callable=AsyncMock,
    ):
        upload_response = await client.post(
            "/upload",
            headers=auth_headers(token),
            files={"file": ("sample.jpeg", b"jpeg-bytes", "image/jpeg")},
        )

    image_id = upload_response.json()["image_id"]
    response = await client.get(
        f"/upload/{image_id}/status",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json() == {"image_id": image_id, "status": "processing"}


@pytest.mark.asyncio
async def test_upload_rejects_invalid_token(client: AsyncClient) -> None:
    response = await client.post(
        "/upload",
        headers=auth_headers("invalid-token"),
        files={"file": ("sample.png", b"image", "image/png")},
    )

    assert response.status_code == 401
