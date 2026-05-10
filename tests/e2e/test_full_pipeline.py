from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx

from conftest import (
    RESULTS_URL,
    TEST_PASSWORD,
    assert_valid_result_payload,
    make_test_email,
    service_urls,
)


def test_health_all_services_are_up() -> None:
    for service_name, base_url in service_urls().items():
        response = httpx.get(f"{base_url}/health", timeout=5.0)

        assert response.status_code == 200, service_name
        assert response.json()["status"] == "ok"


def test_register_and_login_flow(
    create_user: Callable[[str, str, str], dict[str, Any]],
    login: Callable[[str, str], str],
    user_tenant_a: dict[str, Any],
) -> None:
    email = make_test_email("register-login")
    create_user(email, TEST_PASSWORD, user_tenant_a["tenant_id"])

    token = login(email, TEST_PASSWORD)

    assert token
    assert token.count(".") == 2


def test_upload_returns_image_id_and_processing_status(
    upload_image: Callable[[str, Path], str],
    sample_handwriting_image: Path,
    user_tenant_a: dict[str, Any],
) -> None:
    image_id = upload_image(user_tenant_a["token"], sample_handwriting_image)

    assert image_id


def test_full_pipeline_image_reaches_completed_status(
    upload_image: Callable[[str, Path], str],
    wait_for_result: Callable[[str, str, int], dict[str, Any]],
    sample_handwriting_image: Path,
    user_tenant_a: dict[str, Any],
) -> None:
    image_id = upload_image(user_tenant_a["token"], sample_handwriting_image)

    result = wait_for_result(image_id, user_tenant_a["token"], 45)

    assert result["status"] == "completed"


def test_full_pipeline_result_has_valid_emotion(
    upload_image: Callable[[str, Path], str],
    wait_for_result: Callable[[str, str, int], dict[str, Any]],
    sample_handwriting_image: Path,
    user_tenant_a: dict[str, Any],
) -> None:
    image_id = upload_image(user_tenant_a["token"], sample_handwriting_image)

    result = wait_for_result(image_id, user_tenant_a["token"], 45)

    assert result["emotion"] in {"neutral", "anxiety", "stress", "depression"}


def test_full_pipeline_result_confidence_between_0_and_1(
    upload_image: Callable[[str, Path], str],
    wait_for_result: Callable[[str, str, int], dict[str, Any]],
    sample_handwriting_image: Path,
    user_tenant_a: dict[str, Any],
) -> None:
    image_id = upload_image(user_tenant_a["token"], sample_handwriting_image)

    result = wait_for_result(image_id, user_tenant_a["token"], 45)

    assert 0.0 <= result["confidence"] <= 1.0


def test_full_pipeline_result_has_all_4_scores(
    upload_image: Callable[[str, Path], str],
    wait_for_result: Callable[[str, str, int], dict[str, Any]],
    sample_handwriting_image: Path,
    user_tenant_a: dict[str, Any],
) -> None:
    image_id = upload_image(user_tenant_a["token"], sample_handwriting_image)

    result = wait_for_result(image_id, user_tenant_a["token"], 45)

    assert set(result["scores"]) == {"neutral", "anxiety", "stress", "depression"}


def test_multiple_uploads_all_complete_successfully(
    upload_image: Callable[[str, Path], str],
    wait_for_result: Callable[[str, str, int], dict[str, Any]],
    sample_handwriting_image: Path,
    user_tenant_a: dict[str, Any],
) -> None:
    image_ids = [
        upload_image(user_tenant_a["token"], sample_handwriting_image)
        for _ in range(3)
    ]

    results = [
        wait_for_result(image_id, user_tenant_a["token"], 45)
        for image_id in image_ids
    ]

    assert len(results) == 3
    for result in results:
        assert_valid_result_payload(result)


def test_results_list_grows_after_upload(
    upload_image: Callable[[str, Path], str],
    wait_for_result: Callable[[str, str, int], dict[str, Any]],
    sample_handwriting_image: Path,
    user_tenant_a: dict[str, Any],
) -> None:
    before = httpx.get(
        f"{RESULTS_URL}/results",
        headers=user_tenant_a["headers"],
        timeout=10.0,
    )
    assert before.status_code == 200, before.text
    before_count = len(before.json())

    image_id = upload_image(user_tenant_a["token"], sample_handwriting_image)
    wait_for_result(image_id, user_tenant_a["token"], 45)

    after = httpx.get(
        f"{RESULTS_URL}/results",
        headers=user_tenant_a["headers"],
        timeout=10.0,
    )

    assert after.status_code == 200, after.text
    assert len(after.json()) >= before_count + 1
