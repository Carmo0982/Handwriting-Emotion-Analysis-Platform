from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from app.core.results_store import get_result, save_result
from conftest import DUMMY_PREDICTION, TEST_IMAGE_ID, TEST_TENANT_ID, TEST_USER_ID


def test_save_result_writes_item_to_dynamodb(mock_dynamodb: Any) -> None:
    save_result(TEST_IMAGE_ID, TEST_TENANT_ID, TEST_USER_ID, dict(DUMMY_PREDICTION))

    response = mock_dynamodb.get_item(
        Key={"tenant_id": TEST_TENANT_ID, "image_id": TEST_IMAGE_ID}
    )
    assert "Item" in response


def test_save_result_partition_key_is_tenant_id(mock_dynamodb: Any) -> None:
    save_result(TEST_IMAGE_ID, TEST_TENANT_ID, TEST_USER_ID, dict(DUMMY_PREDICTION))

    item = get_result(TEST_IMAGE_ID, TEST_TENANT_ID)

    assert item is not None
    assert item["tenant_id"] == TEST_TENANT_ID


def test_save_result_sort_key_is_image_id(mock_dynamodb: Any) -> None:
    save_result(TEST_IMAGE_ID, TEST_TENANT_ID, TEST_USER_ID, dict(DUMMY_PREDICTION))

    item = get_result(TEST_IMAGE_ID, TEST_TENANT_ID)

    assert item is not None
    assert item["image_id"] == TEST_IMAGE_ID


def test_save_result_includes_created_at_timestamp(mock_dynamodb: Any) -> None:
    save_result(TEST_IMAGE_ID, TEST_TENANT_ID, TEST_USER_ID, dict(DUMMY_PREDICTION))

    item = get_result(TEST_IMAGE_ID, TEST_TENANT_ID)

    assert item is not None
    assert "created_at" in item


def test_save_result_created_at_is_valid_iso8601(mock_dynamodb: Any) -> None:
    save_result(TEST_IMAGE_ID, TEST_TENANT_ID, TEST_USER_ID, dict(DUMMY_PREDICTION))

    item = get_result(TEST_IMAGE_ID, TEST_TENANT_ID)

    assert item is not None
    datetime.fromisoformat(item["created_at"])


def test_save_result_stores_all_4_emotion_scores(mock_dynamodb: Any) -> None:
    save_result(TEST_IMAGE_ID, TEST_TENANT_ID, TEST_USER_ID, dict(DUMMY_PREDICTION))

    item = get_result(TEST_IMAGE_ID, TEST_TENANT_ID)

    assert item is not None
    assert set(item["scores"]) == {"neutral", "anxiety", "stress", "depression"}
    assert item["scores"]["neutral"] == Decimal("0.9")


def test_get_result_returns_item_by_image_id_and_tenant_id(mock_dynamodb: Any) -> None:
    save_result(TEST_IMAGE_ID, TEST_TENANT_ID, TEST_USER_ID, dict(DUMMY_PREDICTION))

    item = get_result(TEST_IMAGE_ID, TEST_TENANT_ID)

    assert item is not None
    assert item["image_id"] == TEST_IMAGE_ID


def test_get_result_returns_none_for_wrong_tenant_id(mock_dynamodb: Any) -> None:
    save_result(TEST_IMAGE_ID, TEST_TENANT_ID, TEST_USER_ID, dict(DUMMY_PREDICTION))

    item = get_result(TEST_IMAGE_ID, "wrong-tenant")

    assert item is None


def test_get_result_returns_none_for_nonexistent_image_id(mock_dynamodb: Any) -> None:
    save_result(TEST_IMAGE_ID, TEST_TENANT_ID, TEST_USER_ID, dict(DUMMY_PREDICTION))

    item = get_result("missing-image", TEST_TENANT_ID)

    assert item is None
