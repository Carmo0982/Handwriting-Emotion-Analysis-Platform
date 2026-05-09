from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from functools import lru_cache
from typing import Any

from app.core.config import settings


@lru_cache
def get_dynamodb_resource() -> Any:
    import boto3

    resource_options: dict[str, Any] = {
        "service_name": "dynamodb",
        "region_name": settings.aws_region,
    }
    if settings.dynamodb_endpoint_url:
        resource_options["endpoint_url"] = settings.dynamodb_endpoint_url
    if settings.aws_access_key_id and settings.aws_secret_access_key:
        resource_options["aws_access_key_id"] = settings.aws_access_key_id
        resource_options["aws_secret_access_key"] = settings.aws_secret_access_key

    return boto3.resource(**resource_options)


def save_result(
    image_id: str,
    tenant_id: str,
    user_id: str,
    prediction: dict[str, Any],
) -> None:
    item = {
        "tenant_id": tenant_id,
        "image_id": image_id,
        "user_id": user_id,
        "emotion": prediction.get("emotion", "unknown"),
        "confidence": prediction.get("confidence", 0.0),
        "scores": prediction.get("scores", {}),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": prediction.get("status", "completed"),
    }
    if "error" in prediction:
        item["error"] = str(prediction["error"])

    table = get_dynamodb_resource().Table(settings.dynamodb_table_name)
    table.put_item(Item=_to_dynamodb_item(item))


def get_result(image_id: str, tenant_id: str) -> dict[str, Any] | None:
    table = get_dynamodb_resource().Table(settings.dynamodb_table_name)
    response = table.get_item(Key={"tenant_id": tenant_id, "image_id": image_id})
    return response.get("Item")


def _to_dynamodb_item(value: Any) -> Any:
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {key: _to_dynamodb_item(child) for key, child in value.items()}
    if isinstance(value, list):
        return [_to_dynamodb_item(child) for child in value]
    return value
