from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

import boto3
import pytest
from fastapi.testclient import TestClient
from jose import jwt
from moto import mock_aws

from app.core.config import settings
from app.core.dynamo import get_dynamodb_resource
from app.main import app


TEST_TENANT_ID = UUID("11111111-1111-1111-1111-111111111111")
OTHER_TENANT_ID = UUID("99999999-9999-9999-9999-999999999999")
TEST_USER_ID = UUID("22222222-2222-2222-2222-222222222222")
OTHER_USER_ID = UUID("88888888-8888-8888-8888-888888888888")


@pytest.fixture(autouse=True)
def clear_dynamo_client() -> None:
    get_dynamodb_resource.cache_clear()


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@mock_aws
def test_get_result_uses_tenant_from_jwt(client: TestClient) -> None:
    create_results_table()
    put_result(
        tenant_id=str(TEST_TENANT_ID),
        image_id="image-123",
        user_id=str(TEST_USER_ID),
        emotion="stress",
        confidence=Decimal("0.91"),
    )

    response = client.get(
        "/results/image-123",
        headers=auth_headers(),
    )

    assert response.status_code == 200
    assert response.json()["image_id"] == "image-123"
    assert response.json()["emotion"] == "stress"
    assert response.json()["confidence"] == 0.91


@mock_aws
def test_get_result_returns_404_for_other_tenant(client: TestClient) -> None:
    create_results_table()
    put_result(
        tenant_id=str(OTHER_TENANT_ID),
        image_id="image-123",
        user_id=str(TEST_USER_ID),
        emotion="stress",
        confidence=Decimal("0.91"),
    )

    response = client.get(
        "/results/image-123",
        headers=auth_headers(),
    )

    assert response.status_code == 404


@mock_aws
def test_list_results_filters_by_tenant_user_and_emotion(client: TestClient) -> None:
    create_results_table()
    now = datetime.now(timezone.utc)
    put_result(
        tenant_id=str(TEST_TENANT_ID),
        image_id="image-stress",
        user_id=str(TEST_USER_ID),
        emotion="stress",
        confidence=Decimal("0.8"),
        created_at=(now - timedelta(minutes=2)).isoformat(),
    )
    put_result(
        tenant_id=str(TEST_TENANT_ID),
        image_id="image-anxiety",
        user_id=str(TEST_USER_ID),
        emotion="anxiety",
        confidence=Decimal("0.7"),
        created_at=(now - timedelta(minutes=1)).isoformat(),
    )
    put_result(
        tenant_id=str(TEST_TENANT_ID),
        image_id="image-other-user",
        user_id=str(OTHER_USER_ID),
        emotion="stress",
        confidence=Decimal("0.9"),
        created_at=now.isoformat(),
    )
    put_result(
        tenant_id=str(OTHER_TENANT_ID),
        image_id="image-other-tenant",
        user_id=str(TEST_USER_ID),
        emotion="stress",
        confidence=Decimal("0.95"),
        created_at=now.isoformat(),
    )

    response = client.get(
        "/results?limit=20&emotion=stress",
        headers=auth_headers(),
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["image_id"] == "image-stress"


@mock_aws
def test_results_summary_is_scoped_to_authenticated_user(client: TestClient) -> None:
    create_results_table()
    now = datetime.now(timezone.utc)
    put_result(
        tenant_id=str(TEST_TENANT_ID),
        image_id="image-neutral",
        user_id=str(TEST_USER_ID),
        emotion="neutral",
        confidence=Decimal("0.6"),
        created_at=(now - timedelta(days=1)).isoformat(),
    )
    put_result(
        tenant_id=str(TEST_TENANT_ID),
        image_id="image-stress",
        user_id=str(TEST_USER_ID),
        emotion="stress",
        confidence=Decimal("0.8"),
        created_at=now.isoformat(),
    )
    put_result(
        tenant_id=str(TEST_TENANT_ID),
        image_id="image-other-user",
        user_id=str(OTHER_USER_ID),
        emotion="depression",
        confidence=Decimal("0.9"),
        created_at=now.isoformat(),
    )

    response = client.get("/results/summary", headers=auth_headers())

    assert response.status_code == 200
    data = response.json()
    assert data["total_analyses"] == 2
    assert data["emotion_distribution"]["neutral"] == 50.0
    assert data["emotion_distribution"]["stress"] == 50.0
    assert data["emotion_distribution"]["depression"] == 0.0
    assert data["last_analysis_date"] == now.isoformat()


def auth_headers(
    user_id: UUID = TEST_USER_ID,
    tenant_id: UUID = TEST_TENANT_ID,
) -> dict[str, str]:
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": str(user_id),
            "tenant_id": str(tenant_id),
            "iat": now,
            "exp": now + timedelta(minutes=15),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return {"Authorization": f"Bearer {token}"}


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


def put_result(
    tenant_id: str,
    image_id: str,
    user_id: str,
    emotion: str,
    confidence: Decimal,
    created_at: str | None = None,
) -> None:
    table = boto3.resource("dynamodb", region_name=settings.aws_region).Table(
        settings.dynamodb_table_name
    )
    timestamp = created_at or datetime.now(timezone.utc).isoformat()
    table.put_item(
        Item={
            "tenant_id": tenant_id,
            "image_id": image_id,
            "user_id": user_id,
            "emotion": emotion,
            "confidence": confidence,
            "scores": {
                "neutral": Decimal("0.1"),
                "anxiety": Decimal("0.1"),
                "stress": confidence,
                "depression": Decimal("0.1"),
            },
            "status": "completed",
            "created_at": timestamp,
        }
    )
