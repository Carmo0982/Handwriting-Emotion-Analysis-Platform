from __future__ import annotations

import json
import logging
from typing import Any
from unittest.mock import Mock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.consumer import PreprocessingConsumer, build_processed_s3_key
from app.main import app
from conftest import TEST_BUCKET, TEST_IMAGE_ID, TEST_TENANT_ID, TEST_ORIGINAL_KEY


def test_consumer_downloads_image_from_s3_on_event(
    mock_s3: Any,
    handwriting_image_bytes: bytes,
    upload_event_payload: dict[str, str],
    fake_kafka_producer: Mock,
) -> None:
    mock_s3.put_object(Bucket=TEST_BUCKET, Key=TEST_ORIGINAL_KEY, Body=handwriting_image_bytes)

    with patch("app.consumer.download_from_s3", wraps=__import__(
        "app.core.storage", fromlist=["download_from_s3"]
    ).download_from_s3) as download_mock, patch(
        "app.consumer.publish_image_preprocessed"
    ):
        PreprocessingConsumer().process_upload_event(upload_event_payload, fake_kafka_producer)

    download_mock.assert_called_once_with(TEST_ORIGINAL_KEY)


def test_consumer_calls_preprocess_with_image_bytes(
    mock_s3: Any,
    handwriting_image_bytes: bytes,
    upload_event_payload: dict[str, str],
    fake_kafka_producer: Mock,
) -> None:
    mock_s3.put_object(Bucket=TEST_BUCKET, Key=TEST_ORIGINAL_KEY, Body=handwriting_image_bytes)

    with patch("app.consumer.preprocess", return_value=b"processed") as preprocess_mock, patch(
        "app.consumer.publish_image_preprocessed"
    ):
        PreprocessingConsumer().process_upload_event(upload_event_payload, fake_kafka_producer)

    preprocess_mock.assert_called_once_with(handwriting_image_bytes)


def test_consumer_uploads_processed_image_to_s3(
    mock_s3: Any,
    handwriting_image_bytes: bytes,
    upload_event_payload: dict[str, str],
    fake_kafka_producer: Mock,
) -> None:
    mock_s3.put_object(Bucket=TEST_BUCKET, Key=TEST_ORIGINAL_KEY, Body=handwriting_image_bytes)
    processed_key = build_processed_s3_key(TEST_ORIGINAL_KEY)

    with patch("app.consumer.preprocess", return_value=b"processed-image"), patch(
        "app.consumer.publish_image_preprocessed"
    ):
        PreprocessingConsumer().process_upload_event(upload_event_payload, fake_kafka_producer)

    response = mock_s3.get_object(Bucket=TEST_BUCKET, Key=processed_key)
    assert response["Body"].read() == b"processed-image"


def test_consumer_processed_s3_key_has_processed_suffix() -> None:
    processed_key = build_processed_s3_key(TEST_ORIGINAL_KEY)

    assert processed_key.endswith("_processed.png")


def test_consumer_publishes_event_after_processing(
    mock_s3: Any,
    handwriting_image_bytes: bytes,
    upload_event_payload: dict[str, str],
    fake_kafka_producer: Mock,
) -> None:
    mock_s3.put_object(Bucket=TEST_BUCKET, Key=TEST_ORIGINAL_KEY, Body=handwriting_image_bytes)

    with patch("app.consumer.preprocess", return_value=b"processed-image"), patch(
        "app.consumer.publish_image_preprocessed"
    ) as publish_mock:
        PreprocessingConsumer().process_upload_event(upload_event_payload, fake_kafka_producer)

    publish_mock.assert_called_once()


def test_consumer_published_event_contains_original_image_id(
    mock_s3: Any,
    handwriting_image_bytes: bytes,
    upload_event_payload: dict[str, str],
    fake_kafka_producer: Mock,
) -> None:
    payload = process_and_get_published_payload(
        mock_s3,
        handwriting_image_bytes,
        upload_event_payload,
        fake_kafka_producer,
    )

    assert payload["image_id"] == TEST_IMAGE_ID


def test_consumer_published_event_contains_tenant_id(
    mock_s3: Any,
    handwriting_image_bytes: bytes,
    upload_event_payload: dict[str, str],
    fake_kafka_producer: Mock,
) -> None:
    payload = process_and_get_published_payload(
        mock_s3,
        handwriting_image_bytes,
        upload_event_payload,
        fake_kafka_producer,
    )

    assert payload["tenant_id"] == TEST_TENANT_ID


def test_consumer_continues_after_corrupt_image(
    mock_s3: Any,
    corrupt_bytes: bytes,
    upload_event_payload: dict[str, str],
    fake_kafka_consumer: Any,
    fake_kafka_producer: Mock,
) -> None:
    mock_s3.put_object(Bucket=TEST_BUCKET, Key=TEST_ORIGINAL_KEY, Body=corrupt_bytes)
    raw_value = json.dumps(upload_event_payload).encode("utf-8")

    PreprocessingConsumer()._handle_message_safely(
        raw_value=raw_value,
        consumer=fake_kafka_consumer,
        producer=fake_kafka_producer,
    )

    fake_kafka_consumer.commit.assert_called_once()


def test_consumer_logs_error_on_processing_failure(
    mock_s3: Any,
    corrupt_bytes: bytes,
    upload_event_payload: dict[str, str],
    fake_kafka_consumer: Any,
    fake_kafka_producer: Mock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    mock_s3.put_object(Bucket=TEST_BUCKET, Key=TEST_ORIGINAL_KEY, Body=corrupt_bytes)
    raw_value = json.dumps(upload_event_payload).encode("utf-8")

    with caplog.at_level(logging.ERROR, logger="app.consumer"):
        PreprocessingConsumer()._handle_message_safely(
            raw_value=raw_value,
            consumer=fake_kafka_consumer,
            producer=fake_kafka_producer,
        )

    assert "Image preprocessing failed; skipping message" in caplog.text


@pytest.mark.asyncio
async def test_health_returns_ok_and_consumer_running() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "consumer": "running"}


def process_and_get_published_payload(
    mock_s3: Any,
    image_bytes: bytes,
    upload_event_payload: dict[str, str],
    fake_kafka_producer: Mock,
) -> dict[str, str]:
    mock_s3.put_object(Bucket=TEST_BUCKET, Key=TEST_ORIGINAL_KEY, Body=image_bytes)

    with patch("app.consumer.preprocess", return_value=b"processed-image"), patch(
        "app.consumer.publish_image_preprocessed"
    ) as publish_mock:
        PreprocessingConsumer().process_upload_event(
            upload_event_payload,
            fake_kafka_producer,
        )

    _, payload = publish_mock.call_args.args
    return payload
