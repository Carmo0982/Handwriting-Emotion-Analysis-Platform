from __future__ import annotations

from decimal import Decimal
from typing import Any
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

import app.main as main_module
from app.consumer import InferenceConsumer
from app.main import app
from conftest import (
    FailingDummyEngine,
    TEST_IMAGE_BYTES,
    TEST_IMAGE_ID,
    TEST_S3_KEY,
    TEST_TENANT_ID,
    TEST_USER_ID,
    get_item,
)


def test_consumer_downloads_image_from_correct_s3_key(
    mock_aws_services: tuple[Any, Any],
    mock_inference_engine: Any,
    mock_kafka_event: dict[str, str],
) -> None:
    del mock_aws_services, mock_inference_engine

    with patch("app.consumer.download_from_s3", wraps=__import__(
        "app.core.storage", fromlist=["download_from_s3"]
    ).download_from_s3) as download_mock:
        InferenceConsumer().process_preprocessed_event(mock_kafka_event)

    download_mock.assert_called_once_with(TEST_S3_KEY)


def test_consumer_calls_predict_with_image_bytes(
    mock_aws_services: tuple[Any, Any],
    mock_inference_engine: Any,
    mock_kafka_event: dict[str, str],
) -> None:
    del mock_aws_services

    InferenceConsumer().process_preprocessed_event(mock_kafka_event)

    mock_inference_engine.predict.assert_called_once_with(TEST_IMAGE_BYTES)


def test_consumer_saves_result_to_dynamodb_after_predict(
    mock_aws_services: tuple[Any, Any],
    mock_inference_engine: Any,
    mock_kafka_event: dict[str, str],
) -> None:
    del mock_inference_engine
    _, table = mock_aws_services

    InferenceConsumer().process_preprocessed_event(mock_kafka_event)

    assert get_item(table)["image_id"] == TEST_IMAGE_ID


def test_consumer_saved_result_contains_emotion(
    mock_aws_services: tuple[Any, Any],
    mock_inference_engine: Any,
    mock_kafka_event: dict[str, str],
) -> None:
    del mock_inference_engine
    _, table = mock_aws_services

    InferenceConsumer().process_preprocessed_event(mock_kafka_event)

    assert get_item(table)["emotion"] == "neutral"


def test_consumer_saved_result_contains_confidence(
    mock_aws_services: tuple[Any, Any],
    mock_inference_engine: Any,
    mock_kafka_event: dict[str, str],
) -> None:
    del mock_inference_engine
    _, table = mock_aws_services

    InferenceConsumer().process_preprocessed_event(mock_kafka_event)

    assert get_item(table)["confidence"] == Decimal("0.9")


def test_consumer_saved_result_contains_tenant_id(
    mock_aws_services: tuple[Any, Any],
    mock_inference_engine: Any,
    mock_kafka_event: dict[str, str],
) -> None:
    del mock_inference_engine
    _, table = mock_aws_services

    InferenceConsumer().process_preprocessed_event(mock_kafka_event)

    assert get_item(table)["tenant_id"] == TEST_TENANT_ID


def test_consumer_saved_result_contains_user_id(
    mock_aws_services: tuple[Any, Any],
    mock_inference_engine: Any,
    mock_kafka_event: dict[str, str],
) -> None:
    del mock_inference_engine
    _, table = mock_aws_services

    InferenceConsumer().process_preprocessed_event(mock_kafka_event)

    assert get_item(table)["user_id"] == TEST_USER_ID


def test_consumer_saved_result_status_is_completed(
    mock_aws_services: tuple[Any, Any],
    mock_inference_engine: Any,
    mock_kafka_event: dict[str, str],
) -> None:
    del mock_inference_engine
    _, table = mock_aws_services

    InferenceConsumer().process_preprocessed_event(mock_kafka_event)

    assert get_item(table)["status"] == "completed"


def test_consumer_saves_failed_status_when_s3_key_not_found(
    mock_aws_services: tuple[Any, Any],
    mock_inference_engine: Any,
    mock_kafka_event_invalid_s3_key: dict[str, str],
) -> None:
    del mock_inference_engine
    _, table = mock_aws_services

    InferenceConsumer().process_preprocessed_event(mock_kafka_event_invalid_s3_key)

    assert get_item(table)["status"] == "failed"


def test_consumer_saves_failed_status_when_model_raises_exception(
    mock_aws_services: tuple[Any, Any],
    mock_kafka_event: dict[str, str],
) -> None:
    _, table = mock_aws_services

    InferenceConsumer(engine=FailingDummyEngine()).process_preprocessed_event(
        mock_kafka_event
    )

    item = get_item(table)
    assert item["status"] == "failed"
    assert item["emotion"] == "unknown"


def test_consumer_does_not_crash_on_inference_error(
    mock_aws_services: tuple[Any, Any],
    mock_kafka_event: dict[str, str],
) -> None:
    del mock_aws_services

    InferenceConsumer(engine=FailingDummyEngine()).process_preprocessed_event(
        mock_kafka_event
    )


def test_consumer_does_not_crash_on_s3_error(
    mock_aws_services: tuple[Any, Any],
    mock_inference_engine: Any,
    mock_kafka_event_invalid_s3_key: dict[str, str],
) -> None:
    del mock_aws_services, mock_inference_engine

    InferenceConsumer().process_preprocessed_event(mock_kafka_event_invalid_s3_key)


@pytest.mark.asyncio
async def test_health_returns_ok_and_model_loaded_true() -> None:
    main_module.inference_consumer = InferenceConsumer(engine=object())

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "model_loaded": True}


@pytest.mark.asyncio
async def test_health_returns_model_loaded_false_when_model_not_initialized() -> None:
    class NotInitializedConsumer:
        is_model_loaded = False

    main_module.inference_consumer = NotInitializedConsumer()  # type: ignore[assignment]

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json()["model_loaded"] is False
