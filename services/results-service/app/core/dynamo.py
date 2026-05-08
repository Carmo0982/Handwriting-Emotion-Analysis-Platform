from __future__ import annotations

from decimal import Decimal
from functools import lru_cache
from typing import Any, Mapping, Optional

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


def get_result_by_id(image_id: str, tenant_id: str) -> Optional[dict[str, Any]]:
    table = get_dynamodb_resource().Table(settings.dynamodb_table_name)
    response = table.get_item(Key={"tenant_id": tenant_id, "image_id": image_id})
    item = response.get("Item")
    if item is None:
        return None
    return _from_dynamodb_item(item)


def get_results_by_user(
    tenant_id: str,
    user_id: str,
    filters: Mapping[str, Any],
) -> list[dict[str, Any]]:
    from boto3.dynamodb.conditions import Attr, Key

    table = get_dynamodb_resource().Table(settings.dynamodb_table_name)
    filter_expression = Attr("user_id").eq(user_id)

    emotion = filters.get("emotion")
    if emotion:
        filter_expression = filter_expression & Attr("emotion").eq(str(emotion))

    date_from = filters.get("date_from")
    if date_from:
        filter_expression = filter_expression & Attr("created_at").gte(str(date_from))

    date_to = filters.get("date_to")
    if date_to:
        filter_expression = filter_expression & Attr("created_at").lte(str(date_to))

    response = table.query(
        KeyConditionExpression=Key("tenant_id").eq(tenant_id),
        FilterExpression=filter_expression,
    )
    items = [_from_dynamodb_item(item) for item in response.get("Items", [])]

    while "LastEvaluatedKey" in response:
        response = table.query(
            KeyConditionExpression=Key("tenant_id").eq(tenant_id),
            FilterExpression=filter_expression,
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )
        items.extend(_from_dynamodb_item(item) for item in response.get("Items", []))

    items.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)
    limit = filters.get("limit")
    if limit is not None:
        return items[: int(limit)]
    return items


def _from_dynamodb_item(value: Any) -> Any:
    if isinstance(value, Decimal):
        if value % 1 == 0:
            return int(value)
        return float(value)
    if isinstance(value, dict):
        return {key: _from_dynamodb_item(child) for key, child in value.items()}
    if isinstance(value, list):
        return [_from_dynamodb_item(child) for child in value]
    return value
