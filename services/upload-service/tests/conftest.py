from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from io import BytesIO
from typing import Any
from unittest.mock import AsyncMock, patch
from uuid import UUID

import boto3
import pytest
import pytest_asyncio
from fastapi import HTTPException, Request, status
from httpx import ASGITransport, AsyncClient
from moto import mock_aws
from PIL import Image

from app.core.config import settings
from app.core.storage import get_s3_client
from app.dependencies import get_current_user
from app.main import app
from app.services.upload_service import clear_image_status_store


TEST_USER_ID = UUID("22222222-2222-2222-2222-222222222222")
TEST_TENANT_ID = UUID("11111111-1111-1111-1111-111111111111")
OTHER_TENANT_ID = UUID("33333333-3333-3333-3333-333333333333")
TEST_BUCKET = "tdse-images-test"
TEST_TOKEN = "test-token"


@pytest.fixture(autouse=True)
def reset_status_store() -> Iterator[None]:
    clear_image_status_store()
    yield
    clear_image_status_store()


@pytest.fixture()
def mock_s3(monkeypatch: pytest.MonkeyPatch) -> Iterator[Any]:
    with mock_aws():
        monkeypatch.setattr(settings, "s3_bucket_name", TEST_BUCKET)
        monkeypatch.setattr(settings, "s3_endpoint_url", "")
        monkeypatch.setattr(settings, "aws_access_key_id", "testing")
        monkeypatch.setattr(settings, "aws_secret_access_key", "testing")
        get_s3_client.cache_clear()

        s3_client = boto3.client("s3", region_name=settings.aws_region)
        s3_client.create_bucket(Bucket=TEST_BUCKET)
        yield s3_client

        get_s3_client.cache_clear()


@pytest.fixture()
def mock_kafka() -> Iterator[AsyncMock]:
    with patch(
        "app.services.upload_service.publish_event",
        new_callable=AsyncMock,
    ) as publish_mock:
        yield publish_mock


@pytest.fixture()
def mock_current_user() -> Iterator[dict[str, UUID]]:
    context = {"user_id": TEST_USER_ID, "tenant_id": TEST_TENANT_ID}

    async def override_get_current_user(request: Request) -> dict[str, UUID]:
        authorization = request.headers.get("Authorization")
        if authorization != f"Bearer {TEST_TOKEN}":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return context

    app.dependency_overrides[get_current_user] = override_get_current_user
    yield context
    app.dependency_overrides.clear()


@pytest_asyncio.fixture()
async def client(
    mock_s3: Any,
    mock_kafka: AsyncMock,
    mock_current_user: dict[str, UUID],
) -> AsyncIterator[AsyncClient]:
    del mock_s3, mock_kafka, mock_current_user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as async_client:
        yield async_client


@pytest.fixture()
def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {TEST_TOKEN}"}


@pytest.fixture()
def sample_png() -> bytes:
    return make_image_bytes("PNG")


@pytest.fixture()
def sample_jpeg() -> bytes:
    return make_image_bytes("JPEG")


@pytest.fixture()
def large_file() -> bytes:
    return b"x" * (settings.max_upload_size_bytes + 1)


def make_image_bytes(image_format: str) -> bytes:
    image = Image.new("RGB", (100, 100), color=(255, 255, 255))
    buffer = BytesIO()
    image.save(buffer, format=image_format)
    return buffer.getvalue()
