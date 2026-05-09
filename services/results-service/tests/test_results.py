from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

import boto3
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from jose import jwt
from moto import mock_aws

from app.core.config import settings
from app.core.dynamo import get_dynamodb_resource
from app.main import app


TENANT_A = UUID("11111111-1111-1111-1111-111111111111")
TENANT_B = UUID("99999999-9999-9999-9999-999999999999")
USER_1 = UUID("22222222-2222-2222-2222-222222222222")
USER_2 = UUID("33333333-3333-3333-3333-333333333333")
USER_3 = UUID("44444444-4444-4444-4444-444444444444")
USER_WITHOUT_RESULTS = UUID("55555555-5555-5555-5555-555555555555")
TABLE_NAME = "inference-results"

SCORES = {
    "neutral": Decimal("0.70"),
    "anxiety": Decimal("0.10"),
    "stress": Decimal("0.10"),
    "depression": Decimal("0.10"),
}


@pytest.fixture(autouse=True)
def clear_dynamo_client() -> Iterator[None]:
    get_dynamodb_resource.cache_clear()
    yield
    get_dynamodb_resource.cache_clear()


@pytest_asyncio.fixture()
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as async_client:
        yield async_client


@pytest.fixture()
def mock_dynamodb(monkeypatch: pytest.MonkeyPatch) -> Iterator[Any]:
    with mock_aws():
        monkeypatch.setattr(settings, "dynamodb_table_name", TABLE_NAME)
        monkeypatch.setattr(settings, "dynamodb_endpoint_url", "")
        monkeypatch.setattr(settings, "aws_access_key_id", "testing")
        monkeypatch.setattr(settings, "aws_secret_access_key", "testing")
        get_dynamodb_resource.cache_clear()

        dynamodb = boto3.resource("dynamodb", region_name=settings.aws_region)
        table = dynamodb.create_table(
            TableName=TABLE_NAME,
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
        for item in seed_items():
            table.put_item(Item=item)
        yield table


@pytest.fixture()
def token_user1() -> str:
    return create_token(user_id=USER_1, tenant_id=TENANT_A)


@pytest.fixture()
def token_user2() -> str:
    return create_token(user_id=USER_2, tenant_id=TENANT_A)


@pytest.fixture()
def token_user3() -> str:
    return create_token(user_id=USER_3, tenant_id=TENANT_B)


@pytest.fixture()
def token_user_without_results() -> str:
    return create_token(user_id=USER_WITHOUT_RESULTS, tenant_id=TENANT_A)


@pytest.fixture()
def headers_user1(token_user1: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token_user1}"}


@pytest.fixture()
def headers_user2(token_user2: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token_user2}"}


@pytest.fixture()
def headers_user3(token_user3: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token_user3}"}


@pytest.fixture()
def headers_user_without_results(token_user_without_results: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token_user_without_results}"}


@pytest.mark.asyncio
async def test_get_result_returns_correct_emotion_and_confidence(
    client: AsyncClient,
    mock_dynamodb: Any,
    headers_user1: dict[str, str],
) -> None:
    del mock_dynamodb

    response = await client.get("/results/u1-stress", headers=headers_user1)

    assert response.status_code == 200
    assert response.json()["emotion"] == "stress"
    assert response.json()["confidence"] == 0.91


@pytest.mark.asyncio
async def test_get_result_returns_all_expected_fields(
    client: AsyncClient,
    mock_dynamodb: Any,
    headers_user1: dict[str, str],
) -> None:
    del mock_dynamodb

    response = await client.get("/results/u1-anxiety", headers=headers_user1)

    assert response.status_code == 200
    assert set(response.json()) == {
        "image_id",
        "emotion",
        "confidence",
        "scores",
        "status",
        "created_at",
    }


@pytest.mark.asyncio
async def test_get_result_wrong_tenant_returns_404(
    client: AsyncClient,
    mock_dynamodb: Any,
    headers_user1: dict[str, str],
) -> None:
    del mock_dynamodb

    response = await client.get("/results/u3-depression", headers=headers_user1)

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_result_nonexistent_image_returns_404(
    client: AsyncClient,
    mock_dynamodb: Any,
    headers_user1: dict[str, str],
) -> None:
    del mock_dynamodb

    response = await client.get("/results/missing-image", headers=headers_user1)

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_result_without_token_returns_401(
    client: AsyncClient,
    mock_dynamodb: Any,
) -> None:
    del mock_dynamodb

    response = await client.get("/results/u1-stress")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_result_user2_cannot_see_user1_results(
    client: AsyncClient,
    mock_dynamodb: Any,
    headers_user2: dict[str, str],
) -> None:
    del mock_dynamodb

    response = await client.get("/results/u1-stress", headers=headers_user2)

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_result_tenant_id_not_accepted_as_query_param(
    client: AsyncClient,
    mock_dynamodb: Any,
    headers_user1: dict[str, str],
) -> None:
    del mock_dynamodb

    response = await client.get(
        f"/results/u1-stress?tenant_id={TENANT_B}",
        headers=headers_user1,
    )

    assert response.status_code == 200
    assert response.json()["image_id"] == "u1-stress"


@pytest.mark.asyncio
async def test_list_results_returns_only_current_user_results(
    client: AsyncClient,
    mock_dynamodb: Any,
    headers_user1: dict[str, str],
) -> None:
    del mock_dynamodb

    response = await client.get("/results", headers=headers_user1)

    assert response.status_code == 200
    assert {item["image_id"] for item in response.json()} == {
        "u1-neutral-old",
        "u1-anxiety",
        "u1-stress",
        "u1-neutral-new",
        "u1-depression",
    }


@pytest.mark.asyncio
async def test_list_results_default_limit_is_20(
    client: AsyncClient,
    mock_dynamodb: Any,
    headers_user1: dict[str, str],
) -> None:
    del mock_dynamodb

    response = await client.get("/results", headers=headers_user1)

    assert response.status_code == 200
    assert len(response.json()) == 5


@pytest.mark.asyncio
async def test_list_results_limit_param_is_respected(
    client: AsyncClient,
    mock_dynamodb: Any,
    headers_user1: dict[str, str],
) -> None:
    del mock_dynamodb

    response = await client.get("/results?limit=2", headers=headers_user1)

    assert response.status_code == 200
    assert len(response.json()) == 2


@pytest.mark.asyncio
async def test_list_results_filter_by_emotion_neutral(
    client: AsyncClient,
    mock_dynamodb: Any,
    headers_user1: dict[str, str],
) -> None:
    del mock_dynamodb

    response = await client.get("/results?emotion=neutral", headers=headers_user1)

    assert response.status_code == 200
    assert len(response.json()) == 2
    assert {item["emotion"] for item in response.json()} == {"neutral"}


@pytest.mark.asyncio
async def test_list_results_filter_by_emotion_anxiety(
    client: AsyncClient,
    mock_dynamodb: Any,
    headers_user1: dict[str, str],
) -> None:
    del mock_dynamodb

    response = await client.get("/results?emotion=anxiety", headers=headers_user1)

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["image_id"] == "u1-anxiety"


@pytest.mark.asyncio
async def test_list_results_filter_by_date_from(
    client: AsyncClient,
    mock_dynamodb: Any,
    headers_user1: dict[str, str],
) -> None:
    del mock_dynamodb

    response = await client.get(
        "/results?date_from=2026-01-04T00:00:00%2B00:00",
        headers=headers_user1,
    )

    assert response.status_code == 200
    assert {item["image_id"] for item in response.json()} == {
        "u1-neutral-new",
        "u1-depression",
    }


@pytest.mark.asyncio
async def test_list_results_filter_by_date_range(
    client: AsyncClient,
    mock_dynamodb: Any,
    headers_user1: dict[str, str],
) -> None:
    del mock_dynamodb

    response = await client.get(
        "/results?date_from=2026-01-02T00:00:00%2B00:00"
        "&date_to=2026-01-03T23:59:59%2B00:00",
        headers=headers_user1,
    )

    assert response.status_code == 200
    assert {item["image_id"] for item in response.json()} == {
        "u1-anxiety",
        "u1-stress",
    }


@pytest.mark.asyncio
async def test_list_results_without_token_returns_401(
    client: AsyncClient,
    mock_dynamodb: Any,
) -> None:
    del mock_dynamodb

    response = await client.get("/results")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_results_tenant_b_user_sees_zero_results_from_tenant_a(
    client: AsyncClient,
    mock_dynamodb: Any,
    headers_user3: dict[str, str],
) -> None:
    del mock_dynamodb

    response = await client.get("/results?emotion=neutral", headers=headers_user3)

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_results_returns_empty_list_not_error_when_no_results(
    client: AsyncClient,
    mock_dynamodb: Any,
    headers_user_without_results: dict[str, str],
) -> None:
    del mock_dynamodb

    response = await client.get("/results", headers=headers_user_without_results)

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_summary_returns_total_analyses_count(
    client: AsyncClient,
    mock_dynamodb: Any,
    headers_user1: dict[str, str],
) -> None:
    del mock_dynamodb

    response = await client.get("/results/summary", headers=headers_user1)

    assert response.status_code == 200
    assert response.json()["total_analyses"] == 5


@pytest.mark.asyncio
async def test_summary_emotion_distribution_has_all_4_emotions(
    client: AsyncClient,
    mock_dynamodb: Any,
    headers_user1: dict[str, str],
) -> None:
    del mock_dynamodb

    response = await client.get("/results/summary", headers=headers_user1)

    assert response.status_code == 200
    assert set(response.json()["emotion_distribution"]) == {
        "neutral",
        "anxiety",
        "stress",
        "depression",
    }


@pytest.mark.asyncio
async def test_summary_emotion_distribution_percentages_sum_to_100(
    client: AsyncClient,
    mock_dynamodb: Any,
    headers_user1: dict[str, str],
) -> None:
    del mock_dynamodb

    response = await client.get("/results/summary", headers=headers_user1)

    assert response.status_code == 200
    percentages = response.json()["emotion_distribution"].values()
    assert round(sum(percentages), 2) == 100.0


@pytest.mark.asyncio
async def test_summary_returns_last_analysis_date(
    client: AsyncClient,
    mock_dynamodb: Any,
    headers_user1: dict[str, str],
) -> None:
    del mock_dynamodb

    response = await client.get("/results/summary", headers=headers_user1)

    assert response.status_code == 200
    assert response.json()["last_analysis_date"] == "2026-01-05T12:00:00+00:00"


@pytest.mark.asyncio
async def test_summary_with_no_results_returns_zeros(
    client: AsyncClient,
    mock_dynamodb: Any,
    headers_user_without_results: dict[str, str],
) -> None:
    del mock_dynamodb

    response = await client.get("/results/summary", headers=headers_user_without_results)

    assert response.status_code == 200
    assert response.json() == {
        "total_analyses": 0,
        "emotion_distribution": {
            "neutral": 0.0,
            "anxiety": 0.0,
            "stress": 0.0,
            "depression": 0.0,
        },
        "last_analysis_date": None,
    }


@pytest.mark.asyncio
async def test_summary_without_token_returns_401(
    client: AsyncClient,
    mock_dynamodb: Any,
) -> None:
    del mock_dynamodb

    response = await client.get("/results/summary")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_summary_only_counts_current_user_results(
    client: AsyncClient,
    mock_dynamodb: Any,
    headers_user2: dict[str, str],
) -> None:
    del mock_dynamodb

    response = await client.get("/results/summary", headers=headers_user2)

    assert response.status_code == 200
    assert response.json()["total_analyses"] == 3


@pytest.mark.asyncio
async def test_tenant_a_cannot_access_tenant_b_results(
    client: AsyncClient,
    mock_dynamodb: Any,
    headers_user1: dict[str, str],
) -> None:
    del mock_dynamodb

    response = await client.get("/results/u3-stress", headers=headers_user1)

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_tenant_b_cannot_access_tenant_a_results(
    client: AsyncClient,
    mock_dynamodb: Any,
    headers_user3: dict[str, str],
) -> None:
    del mock_dynamodb

    response = await client.get("/results/u1-stress", headers=headers_user3)

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_tenant_id_in_jwt_overrides_any_query_param(
    client: AsyncClient,
    mock_dynamodb: Any,
    headers_user1: dict[str, str],
) -> None:
    del mock_dynamodb

    response = await client.get(
        f"/results?tenant_id={TENANT_B}&limit=100",
        headers=headers_user1,
    )

    assert response.status_code == 200
    assert {item["image_id"] for item in response.json()} == {
        "u1-neutral-old",
        "u1-anxiety",
        "u1-stress",
        "u1-neutral-new",
        "u1-depression",
    }


@pytest.mark.asyncio
async def test_all_results_belong_to_authenticated_user_tenant(
    client: AsyncClient,
    mock_dynamodb: Any,
    headers_user1: dict[str, str],
) -> None:
    del mock_dynamodb

    response = await client.get("/results?limit=100", headers=headers_user1)

    assert response.status_code == 200
    assert all(item["image_id"].startswith("u1-") for item in response.json())


@pytest.mark.asyncio
async def test_health_returns_ok(
    client: AsyncClient,
) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": settings.service_name}


def create_token(user_id: UUID, tenant_id: UUID) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": str(user_id),
            "tenant_id": str(tenant_id),
            "iat": now,
            "exp": now + timedelta(minutes=15),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def seed_items() -> list[dict[str, Any]]:
    return [
        result_item(
            tenant_id=TENANT_A,
            user_id=USER_1,
            image_id="u1-neutral-old",
            emotion="neutral",
            confidence=Decimal("0.82"),
            created_at="2026-01-01T12:00:00+00:00",
        ),
        result_item(
            tenant_id=TENANT_A,
            user_id=USER_1,
            image_id="u1-anxiety",
            emotion="anxiety",
            confidence=Decimal("0.76"),
            created_at="2026-01-02T12:00:00+00:00",
        ),
        result_item(
            tenant_id=TENANT_A,
            user_id=USER_1,
            image_id="u1-stress",
            emotion="stress",
            confidence=Decimal("0.91"),
            created_at="2026-01-03T12:00:00+00:00",
        ),
        result_item(
            tenant_id=TENANT_A,
            user_id=USER_1,
            image_id="u1-neutral-new",
            emotion="neutral",
            confidence=Decimal("0.88"),
            created_at="2026-01-04T12:00:00+00:00",
        ),
        result_item(
            tenant_id=TENANT_A,
            user_id=USER_1,
            image_id="u1-depression",
            emotion="depression",
            confidence=Decimal("0.73"),
            created_at="2026-01-05T12:00:00+00:00",
        ),
        result_item(
            tenant_id=TENANT_A,
            user_id=USER_2,
            image_id="u2-neutral",
            emotion="neutral",
            confidence=Decimal("0.80"),
            created_at="2026-01-06T12:00:00+00:00",
        ),
        result_item(
            tenant_id=TENANT_A,
            user_id=USER_2,
            image_id="u2-stress",
            emotion="stress",
            confidence=Decimal("0.84"),
            created_at="2026-01-07T12:00:00+00:00",
        ),
        result_item(
            tenant_id=TENANT_A,
            user_id=USER_2,
            image_id="u2-anxiety",
            emotion="anxiety",
            confidence=Decimal("0.79"),
            created_at="2026-01-08T12:00:00+00:00",
        ),
        result_item(
            tenant_id=TENANT_B,
            user_id=USER_3,
            image_id="u3-depression",
            emotion="depression",
            confidence=Decimal("0.86"),
            created_at="2026-01-09T12:00:00+00:00",
        ),
        result_item(
            tenant_id=TENANT_B,
            user_id=USER_3,
            image_id="u3-stress",
            emotion="stress",
            confidence=Decimal("0.92"),
            created_at="2026-01-10T12:00:00+00:00",
        ),
    ]


def result_item(
    tenant_id: UUID,
    user_id: UUID,
    image_id: str,
    emotion: str,
    confidence: Decimal,
    created_at: str,
) -> dict[str, Any]:
    scores = dict(SCORES)
    scores[emotion] = confidence
    return {
        "tenant_id": str(tenant_id),
        "image_id": image_id,
        "user_id": str(user_id),
        "emotion": emotion,
        "confidence": confidence,
        "scores": scores,
        "status": "completed",
        "created_at": created_at,
    }
