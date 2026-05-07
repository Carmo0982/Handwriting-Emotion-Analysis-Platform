from decimal import Decimal

import boto3
import pytest
from moto import mock_aws

from app.consumer import InferenceConsumer
from app.core.config import settings
from app.core.results_store import get_dynamodb_resource
from app.core.storage import get_s3_client


class FixedDummyEngine:
    def predict(self, image_bytes: bytes) -> dict[str, object]:
        assert image_bytes == b"processed-image"
        return {
            "emotion": "stress",
            "confidence": 0.91,
            "scores": {
                "neutral": 0.01,
                "anxiety": 0.05,
                "stress": 0.91,
                "depression": 0.03,
            },
        }


class FailingDummyEngine:
    def predict(self, image_bytes: bytes) -> dict[str, object]:
        del image_bytes
        raise RuntimeError("model failed")


@pytest.fixture(autouse=True)
def clear_aws_clients() -> None:
    get_s3_client.cache_clear()
    get_dynamodb_resource.cache_clear()


@mock_aws
def test_process_event_saves_completed_prediction() -> None:
    create_s3_object("tenant/user/image_processed.png", b"processed-image")
    create_results_table()

    consumer = InferenceConsumer(engine=FixedDummyEngine())
    consumer.process_preprocessed_event(
        {
            "image_id": "image-123",
            "tenant_id": "tenant-123",
            "user_id": "user-123",
            "s3_key_processed": "tenant/user/image_processed.png",
        }
    )

    item = get_result_item(tenant_id="tenant-123", image_id="image-123")
    assert item["status"] == "completed"
    assert item["emotion"] == "stress"
    assert item["confidence"] == Decimal("0.91")
    assert item["scores"]["stress"] == Decimal("0.91")
    assert item["user_id"] == "user-123"
    assert "created_at" in item


@mock_aws
def test_process_event_saves_failed_status_when_model_fails() -> None:
    create_s3_object("tenant/user/image_processed.png", b"processed-image")
    create_results_table()

    consumer = InferenceConsumer(engine=FailingDummyEngine())
    consumer.process_preprocessed_event(
        {
            "image_id": "image-123",
            "tenant_id": "tenant-123",
            "user_id": "user-123",
            "s3_key_processed": "tenant/user/image_processed.png",
        }
    )

    item = get_result_item(tenant_id="tenant-123", image_id="image-123")
    assert item["status"] == "failed"
    assert item["emotion"] == "unknown"
    assert item["confidence"] == Decimal("0.0")
    assert "model failed" in item["error"]


@mock_aws
def test_process_event_saves_failed_status_when_s3_download_fails() -> None:
    create_results_table()

    consumer = InferenceConsumer(engine=FixedDummyEngine())
    consumer.process_preprocessed_event(
        {
            "image_id": "image-123",
            "tenant_id": "tenant-123",
            "user_id": "user-123",
            "s3_key_processed": "missing-key.png",
        }
    )

    item = get_result_item(tenant_id="tenant-123", image_id="image-123")
    assert item["status"] == "failed"
    assert item["emotion"] == "unknown"


def create_s3_object(key: str, body: bytes) -> None:
    s3_client = boto3.client("s3", region_name=settings.aws_region)
    s3_client.create_bucket(Bucket=settings.s3_bucket_name)
    s3_client.put_object(Bucket=settings.s3_bucket_name, Key=key, Body=body)


def create_results_table() -> None:
    dynamodb = boto3.resource("dynamodb", region_name=settings.aws_region)
    dynamodb.create_table(
        TableName=settings.dynamodb_table_name,
        KeySchema=[
            {"AttributeName": "tenant_id", "KeyType": "HASH"},
            {"AttributeName": "image_id", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "tenant_id", "AttributeType": "S"},
            {"AttributeName": "image_id", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )


def get_result_item(tenant_id: str, image_id: str) -> dict[str, object]:
    table = boto3.resource("dynamodb", region_name=settings.aws_region).Table(
        settings.dynamodb_table_name
    )
    response = table.get_item(Key={"tenant_id": tenant_id, "image_id": image_id})
    return response["Item"]
