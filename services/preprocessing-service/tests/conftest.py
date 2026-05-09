from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from unittest.mock import Mock

import boto3
import cv2
import numpy as np
import pytest
from moto import mock_aws

from app.core.config import settings
from app.core.storage import get_s3_client


TEST_BUCKET = "tdse-preprocessing-test"
TEST_IMAGE_ID = "image-123"
TEST_TENANT_ID = "tenant-123"
TEST_USER_ID = "user-123"
TEST_ORIGINAL_KEY = f"{TEST_TENANT_ID}/{TEST_USER_ID}/{TEST_IMAGE_ID}.png"


@pytest.fixture()
def white_image_bytes() -> bytes:
    return encode_grayscale_png(np.ones((300, 300), dtype=np.uint8) * 255)


@pytest.fixture()
def black_image_bytes() -> bytes:
    return encode_grayscale_png(np.zeros((300, 300), dtype=np.uint8))


@pytest.fixture()
def handwriting_image_bytes() -> bytes:
    image = np.ones((300, 300), dtype=np.uint8) * 255
    cv2.line(image, (50, 100), (250, 100), 0, 2)
    cv2.line(image, (50, 150), (250, 150), 0, 2)
    return encode_grayscale_png(image)


@pytest.fixture()
def noise_image_bytes() -> bytes:
    rng = np.random.default_rng(42)
    image = np.clip(rng.normal(127, 160, (300, 300)), 0, 255).astype(np.uint8)
    return encode_grayscale_png(image)


@pytest.fixture()
def corrupt_bytes() -> bytes:
    return b"not-a-valid-image-\x00\x01\x02"


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
def upload_event_payload() -> dict[str, str]:
    return {
        "image_id": TEST_IMAGE_ID,
        "tenant_id": TEST_TENANT_ID,
        "user_id": TEST_USER_ID,
        "s3_key": TEST_ORIGINAL_KEY,
    }


@pytest.fixture()
def fake_kafka_producer() -> Mock:
    return Mock(name="fake_kafka_producer")


class FakeKafkaConsumer:
    def __init__(self) -> None:
        self.commit = Mock()


@pytest.fixture()
def fake_kafka_consumer() -> FakeKafkaConsumer:
    return FakeKafkaConsumer()


def encode_grayscale_png(image: np.ndarray) -> bytes:
    encoded_successfully, encoded_image = cv2.imencode(".png", image)
    assert encoded_successfully
    return encoded_image.tobytes()


def decode_grayscale_png(image_bytes: bytes) -> np.ndarray:
    image = cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
    assert image is not None
    return image
