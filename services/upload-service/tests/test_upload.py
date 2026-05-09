from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from conftest import (
    OTHER_TENANT_ID,
    TEST_BUCKET,
    TEST_TENANT_ID,
    TEST_USER_ID,
)


@pytest.mark.asyncio
async def test_upload_valid_png_returns_image_id_and_processing_status(
    client: AsyncClient,
    auth_headers: dict[str, str],
    sample_png: bytes,
) -> None:
    response = await client.post(
        "/upload",
        headers=auth_headers,
        files={"file": ("sample.png", sample_png, "image/png")},
    )

    assert response.status_code == 200
    data = response.json()
    assert UUID(data["image_id"])
    assert data["status"] == "processing"


@pytest.mark.asyncio
async def test_upload_valid_jpeg_returns_200(
    client: AsyncClient,
    auth_headers: dict[str, str],
    sample_jpeg: bytes,
) -> None:
    response = await client.post(
        "/upload",
        headers=auth_headers,
        files={"file": ("sample.jpeg", sample_jpeg, "image/jpeg")},
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_upload_without_token_returns_401(
    client: AsyncClient,
    sample_png: bytes,
) -> None:
    response = await client.post(
        "/upload",
        files={"file": ("sample.png", sample_png, "image/png")},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_upload_pdf_file_returns_400(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    response = await client.post(
        "/upload",
        headers=auth_headers,
        files={"file": ("document.pdf", b"%PDF-1.4", "application/pdf")},
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_upload_text_file_returns_400(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    response = await client.post(
        "/upload",
        headers=auth_headers,
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_upload_file_larger_than_10mb_returns_400(
    client: AsyncClient,
    auth_headers: dict[str, str],
    large_file: bytes,
) -> None:
    response = await client.post(
        "/upload",
        headers=auth_headers,
        files={"file": ("large.png", large_file, "image/png")},
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_upload_empty_file_returns_400(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    response = await client.post(
        "/upload",
        headers=auth_headers,
        files={"file": ("empty.png", b"", "image/png")},
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_upload_stores_file_in_s3_with_tenant_id_in_path(
    client: AsyncClient,
    auth_headers: dict[str, str],
    sample_png: bytes,
    mock_s3: Any,
) -> None:
    response = await upload_png(client, auth_headers, sample_png)
    image_id = response.json()["image_id"]
    expected_key = f"{TEST_TENANT_ID}/{TEST_USER_ID}/{image_id}.png"

    s3_response = mock_s3.get_object(Bucket=TEST_BUCKET, Key=expected_key)

    assert s3_response["Body"].read() == sample_png


@pytest.mark.asyncio
async def test_upload_s3_key_format_is_tenantid_userid_imageid(
    client: AsyncClient,
    auth_headers: dict[str, str],
    sample_png: bytes,
    mock_kafka: AsyncMock,
) -> None:
    response = await upload_png(client, auth_headers, sample_png)
    image_id = response.json()["image_id"]
    _, payload = mock_kafka.await_args.args

    assert payload["s3_key"] == f"{TEST_TENANT_ID}/{TEST_USER_ID}/{image_id}.png"


@pytest.mark.asyncio
async def test_upload_publishes_kafka_event_with_correct_fields(
    client: AsyncClient,
    auth_headers: dict[str, str],
    sample_png: bytes,
    mock_kafka: AsyncMock,
) -> None:
    response = await upload_png(client, auth_headers, sample_png)
    image_id = response.json()["image_id"]

    mock_kafka.assert_awaited_once()
    topic, payload = mock_kafka.await_args.args

    assert topic == "image-uploaded"
    assert payload["image_id"] == image_id
    assert payload["tenant_id"] == str(TEST_TENANT_ID)
    assert payload["user_id"] == str(TEST_USER_ID)
    assert payload["s3_key"] == f"{TEST_TENANT_ID}/{TEST_USER_ID}/{image_id}.png"
    assert "timestamp" in payload


@pytest.mark.asyncio
async def test_upload_kafka_event_contains_image_id(
    client: AsyncClient,
    auth_headers: dict[str, str],
    sample_png: bytes,
    mock_kafka: AsyncMock,
) -> None:
    response = await upload_png(client, auth_headers, sample_png)
    _, payload = mock_kafka.await_args.args

    assert payload["image_id"] == response.json()["image_id"]


@pytest.mark.asyncio
async def test_upload_kafka_event_contains_tenant_id(
    client: AsyncClient,
    auth_headers: dict[str, str],
    sample_png: bytes,
    mock_kafka: AsyncMock,
) -> None:
    await upload_png(client, auth_headers, sample_png)
    _, payload = mock_kafka.await_args.args

    assert payload["tenant_id"] == str(TEST_TENANT_ID)


@pytest.mark.asyncio
async def test_upload_kafka_event_contains_s3_key(
    client: AsyncClient,
    auth_headers: dict[str, str],
    sample_png: bytes,
    mock_kafka: AsyncMock,
) -> None:
    response = await upload_png(client, auth_headers, sample_png)
    image_id = response.json()["image_id"]
    _, payload = mock_kafka.await_args.args

    assert payload["s3_key"] == f"{TEST_TENANT_ID}/{TEST_USER_ID}/{image_id}.png"


@pytest.mark.asyncio
async def test_upload_generates_unique_image_id_per_request(
    client: AsyncClient,
    auth_headers: dict[str, str],
    sample_png: bytes,
) -> None:
    first_response = await upload_png(client, auth_headers, sample_png)
    second_response = await upload_png(client, auth_headers, sample_png)

    assert first_response.json()["image_id"] != second_response.json()["image_id"]


@pytest.mark.asyncio
async def test_get_status_returns_processing_for_new_image(
    client: AsyncClient,
    auth_headers: dict[str, str],
    sample_png: bytes,
) -> None:
    upload_response = await upload_png(client, auth_headers, sample_png)
    image_id = upload_response.json()["image_id"]

    response = await client.get(
        f"/upload/{image_id}/status",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json() == {"image_id": image_id, "status": "processing"}


@pytest.mark.asyncio
async def test_get_status_nonexistent_image_returns_404(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    response = await client.get(
        f"/upload/{uuid4()}/status",
        headers=auth_headers,
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_status_without_token_returns_401(client: AsyncClient) -> None:
    response = await client.get(f"/upload/{uuid4()}/status")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_s3_key_always_starts_with_tenant_id(
    client: AsyncClient,
    auth_headers: dict[str, str],
    sample_png: bytes,
    mock_kafka: AsyncMock,
) -> None:
    await upload_png(client, auth_headers, sample_png)
    _, payload = mock_kafka.await_args.args

    assert payload["s3_key"].startswith(f"{TEST_TENANT_ID}/")


@pytest.mark.asyncio
async def test_two_tenants_upload_to_different_s3_paths(
    client: AsyncClient,
    auth_headers: dict[str, str],
    sample_png: bytes,
    mock_current_user: dict[str, UUID],
    mock_s3: Any,
) -> None:
    first_response = await upload_png(client, auth_headers, sample_png)
    first_image_id = first_response.json()["image_id"]

    mock_current_user["tenant_id"] = OTHER_TENANT_ID
    second_response = await upload_png(client, auth_headers, sample_png)
    second_image_id = second_response.json()["image_id"]

    first_key = f"{TEST_TENANT_ID}/{TEST_USER_ID}/{first_image_id}.png"
    second_key = f"{OTHER_TENANT_ID}/{TEST_USER_ID}/{second_image_id}.png"
    s3_objects = mock_s3.list_objects_v2(Bucket=TEST_BUCKET)["Contents"]
    keys = {item["Key"] for item in s3_objects}

    assert first_key in keys
    assert second_key in keys
    assert first_key.split("/")[0] != second_key.split("/")[0]


async def upload_png(
    client: AsyncClient,
    auth_headers: dict[str, str],
    sample_png: bytes,
) -> Any:
    response = await client.post(
        "/upload",
        headers=auth_headers,
        files={"file": ("sample.png", sample_png, "image/png")},
    )
    assert response.status_code == 200
    return response
