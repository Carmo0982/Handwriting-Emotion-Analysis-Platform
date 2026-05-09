from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from unittest.mock import Mock, patch

import boto3
import pytest
from moto import mock_aws

from app.core.config import settings
from app.core.results_store import get_dynamodb_resource
from app.core.storage import get_s3_client


TEST_BUCKET = "tdse-inference-test"
TEST_TABLE = "inference-results"
TEST_IMAGE_ID = "image-123"
TEST_TENANT_ID = "tenant-123"
TEST_USER_ID = "user-123"
TEST_S3_KEY = f"{TEST_TENANT_ID}/{TEST_USER_ID}/{TEST_IMAGE_ID}_processed.png"
TEST_IMAGE_BYTES = b"processed-image"

DUMMY_PREDICTION = {
    "emotion": "neutral",
    "confidence": 0.9,
    "scores": {
        "neutral": 0.9,
        "anxiety": 0.05,
        "stress": 0.03,
        "depression": 0.02,
    },
}


class DummyEngine:
    def __init__(self) -> None:
        self.predict = Mock(return_value=dict(DUMMY_PREDICTION))


class FailingDummyEngine:
    def predict(self, image_bytes: bytes) -> dict[str, Any]:
        del image_bytes
        raise RuntimeError("model failed")


@pytest.fixture(autouse=True)
def clear_aws_clients() -> Iterator[None]:
    get_s3_client.cache_clear()
    get_dynamodb_resource.cache_clear()
    yield
    get_s3_client.cache_clear()
    get_dynamodb_resource.cache_clear()


@pytest.fixture()
def mock_inference_engine() -> Iterator[DummyEngine]:
    engine = DummyEngine()
    with patch("app.consumer.load_inference_engine", return_value=engine):
        yield engine


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
        s3_client.put_object(Bucket=TEST_BUCKET, Key=TEST_S3_KEY, Body=TEST_IMAGE_BYTES)
        yield s3_client


@pytest.fixture()
def mock_dynamodb(monkeypatch: pytest.MonkeyPatch) -> Iterator[Any]:
    with mock_aws():
        monkeypatch.setattr(settings, "dynamodb_table_name", TEST_TABLE)
        monkeypatch.setattr(settings, "dynamodb_endpoint_url", "")
        monkeypatch.setattr(settings, "aws_access_key_id", "testing")
        monkeypatch.setattr(settings, "aws_secret_access_key", "testing")
        get_dynamodb_resource.cache_clear()

        dynamodb = boto3.resource("dynamodb", region_name=settings.aws_region)
        table = dynamodb.create_table(
            TableName=TEST_TABLE,
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
        table.wait_until_exists()
        yield table


@pytest.fixture()
def mock_aws_services(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[Any, Any]]:
    with mock_aws():
        monkeypatch.setattr(settings, "s3_bucket_name", TEST_BUCKET)
        monkeypatch.setattr(settings, "s3_endpoint_url", "")
        monkeypatch.setattr(settings, "dynamodb_table_name", TEST_TABLE)
        monkeypatch.setattr(settings, "dynamodb_endpoint_url", "")
        monkeypatch.setattr(settings, "aws_access_key_id", "testing")
        monkeypatch.setattr(settings, "aws_secret_access_key", "testing")
        get_s3_client.cache_clear()
        get_dynamodb_resource.cache_clear()

        s3_client = boto3.client("s3", region_name=settings.aws_region)
        s3_client.create_bucket(Bucket=TEST_BUCKET)
        s3_client.put_object(Bucket=TEST_BUCKET, Key=TEST_S3_KEY, Body=TEST_IMAGE_BYTES)

        dynamodb = boto3.resource("dynamodb", region_name=settings.aws_region)
        table = dynamodb.create_table(
            TableName=TEST_TABLE,
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
        table.wait_until_exists()
        yield s3_client, table


@pytest.fixture()
def mock_kafka_event() -> dict[str, str]:
    return {
        "image_id": TEST_IMAGE_ID,
        "tenant_id": TEST_TENANT_ID,
        "user_id": TEST_USER_ID,
        "s3_key": TEST_S3_KEY,
    }


@pytest.fixture()
def mock_kafka_event_invalid_s3_key() -> dict[str, str]:
    return {
        "image_id": TEST_IMAGE_ID,
        "tenant_id": TEST_TENANT_ID,
        "user_id": TEST_USER_ID,
        "s3_key": "missing/key.png",
    }


def get_item(table: Any, tenant_id: str = TEST_TENANT_ID, image_id: str = TEST_IMAGE_ID) -> dict[str, Any]:
    response = table.get_item(Key={"tenant_id": tenant_id, "image_id": image_id})
    return response["Item"]
