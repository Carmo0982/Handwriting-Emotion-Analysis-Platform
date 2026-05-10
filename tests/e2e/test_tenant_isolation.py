from __future__ import annotations

import asyncio
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx

from conftest import (
    RESULTS_URL,
    async_upload_image,
    async_wait_for_result,
)


def test_tenant_a_result_not_visible_to_tenant_b(
    upload_image: Callable[[str, Path], str],
    wait_for_result: Callable[[str, str, int], dict[str, Any]],
    sample_handwriting_image: Path,
    user_tenant_a: dict[str, Any],
    user_tenant_b: dict[str, Any],
) -> None:
    image_id = upload_image(user_tenant_a["token"], sample_handwriting_image)
    wait_for_result(image_id, user_tenant_a["token"], 45)

    response = httpx.get(
        f"{RESULTS_URL}/results/{image_id}",
        headers=user_tenant_b["headers"],
        timeout=10.0,
    )

    assert response.status_code == 404


def test_tenant_b_result_not_visible_to_tenant_a(
    upload_image: Callable[[str, Path], str],
    wait_for_result: Callable[[str, str, int], dict[str, Any]],
    sample_handwriting_image: Path,
    user_tenant_a: dict[str, Any],
    user_tenant_b: dict[str, Any],
) -> None:
    image_id = upload_image(user_tenant_b["token"], sample_handwriting_image)
    wait_for_result(image_id, user_tenant_b["token"], 45)

    response = httpx.get(
        f"{RESULTS_URL}/results/{image_id}",
        headers=user_tenant_a["headers"],
        timeout=10.0,
    )

    assert response.status_code == 404


def test_tenant_a_list_contains_only_tenant_a_results(
    upload_image: Callable[[str, Path], str],
    wait_for_result: Callable[[str, str, int], dict[str, Any]],
    sample_handwriting_image: Path,
    user_tenant_a: dict[str, Any],
    user_tenant_b: dict[str, Any],
) -> None:
    tenant_a_image_id = upload_image(user_tenant_a["token"], sample_handwriting_image)
    tenant_b_image_id = upload_image(user_tenant_b["token"], sample_handwriting_image)
    wait_for_result(tenant_a_image_id, user_tenant_a["token"], 45)
    wait_for_result(tenant_b_image_id, user_tenant_b["token"], 45)

    response = httpx.get(
        f"{RESULTS_URL}/results?limit=100",
        headers=user_tenant_a["headers"],
        timeout=10.0,
    )

    assert response.status_code == 200, response.text
    visible_ids = {item["image_id"] for item in response.json()}
    assert tenant_a_image_id in visible_ids
    assert tenant_b_image_id not in visible_ids


def test_tenant_b_list_contains_only_tenant_b_results(
    upload_image: Callable[[str, Path], str],
    wait_for_result: Callable[[str, str, int], dict[str, Any]],
    sample_handwriting_image: Path,
    user_tenant_a: dict[str, Any],
    user_tenant_b: dict[str, Any],
) -> None:
    tenant_a_image_id = upload_image(user_tenant_a["token"], sample_handwriting_image)
    tenant_b_image_id = upload_image(user_tenant_b["token"], sample_handwriting_image)
    wait_for_result(tenant_a_image_id, user_tenant_a["token"], 45)
    wait_for_result(tenant_b_image_id, user_tenant_b["token"], 45)

    response = httpx.get(
        f"{RESULTS_URL}/results?limit=100",
        headers=user_tenant_b["headers"],
        timeout=10.0,
    )

    assert response.status_code == 200, response.text
    visible_ids = {item["image_id"] for item in response.json()}
    assert tenant_b_image_id in visible_ids
    assert tenant_a_image_id not in visible_ids


def test_summary_counts_are_independent_per_tenant(
    upload_image: Callable[[str, Path], str],
    wait_for_result: Callable[[str, str, int], dict[str, Any]],
    sample_handwriting_image: Path,
    user_tenant_a: dict[str, Any],
    user_tenant_b: dict[str, Any],
) -> None:
    tenant_a_ids = [
        upload_image(user_tenant_a["token"], sample_handwriting_image)
        for _ in range(2)
    ]
    tenant_b_id = upload_image(user_tenant_b["token"], sample_handwriting_image)

    for image_id in tenant_a_ids:
        wait_for_result(image_id, user_tenant_a["token"], 45)
    wait_for_result(tenant_b_id, user_tenant_b["token"], 45)

    tenant_a_summary = httpx.get(
        f"{RESULTS_URL}/results/summary",
        headers=user_tenant_a["headers"],
        timeout=10.0,
    )
    tenant_b_summary = httpx.get(
        f"{RESULTS_URL}/results/summary",
        headers=user_tenant_b["headers"],
        timeout=10.0,
    )

    assert tenant_a_summary.status_code == 200, tenant_a_summary.text
    assert tenant_b_summary.status_code == 200, tenant_b_summary.text
    assert tenant_a_summary.json()["total_analyses"] == 2
    assert tenant_b_summary.json()["total_analyses"] == 1


def test_concurrent_uploads_from_two_tenants_do_not_mix_results(
    sample_handwriting_image: Path,
    user_tenant_a: dict[str, Any],
    user_tenant_b: dict[str, Any],
) -> None:
    async def run_concurrent_pipeline() -> tuple[list[str], list[str]]:
        tenant_a_uploads = [
            async_upload_image(user_tenant_a["token"], sample_handwriting_image)
            for _ in range(5)
        ]
        tenant_b_uploads = [
            async_upload_image(user_tenant_b["token"], sample_handwriting_image)
            for _ in range(5)
        ]
        tenant_a_ids, tenant_b_ids = await asyncio.gather(
            asyncio.gather(*tenant_a_uploads),
            asyncio.gather(*tenant_b_uploads),
        )

        await asyncio.gather(
            *[
                async_wait_for_result(image_id, user_tenant_a["token"], 60)
                for image_id in tenant_a_ids
            ],
            *[
                async_wait_for_result(image_id, user_tenant_b["token"], 60)
                for image_id in tenant_b_ids
            ],
        )
        return list(tenant_a_ids), list(tenant_b_ids)

    tenant_a_ids, tenant_b_ids = asyncio.run(run_concurrent_pipeline())

    tenant_a_results = httpx.get(
        f"{RESULTS_URL}/results?limit=100",
        headers=user_tenant_a["headers"],
        timeout=10.0,
    )
    tenant_b_results = httpx.get(
        f"{RESULTS_URL}/results?limit=100",
        headers=user_tenant_b["headers"],
        timeout=10.0,
    )

    assert tenant_a_results.status_code == 200, tenant_a_results.text
    assert tenant_b_results.status_code == 200, tenant_b_results.text

    tenant_a_visible_ids = {item["image_id"] for item in tenant_a_results.json()}
    tenant_b_visible_ids = {item["image_id"] for item in tenant_b_results.json()}

    assert set(tenant_a_ids).issubset(tenant_a_visible_ids)
    assert set(tenant_b_ids).issubset(tenant_b_visible_ids)
    assert set(tenant_a_ids).isdisjoint(tenant_b_visible_ids)
    assert set(tenant_b_ids).isdisjoint(tenant_a_visible_ids)

    for image_id in tenant_a_ids:
        response = httpx.get(
            f"{RESULTS_URL}/results/{image_id}",
            headers=user_tenant_b["headers"],
            timeout=10.0,
        )
        assert response.status_code == 404

    for image_id in tenant_b_ids:
        response = httpx.get(
            f"{RESULTS_URL}/results/{image_id}",
            headers=user_tenant_a["headers"],
            timeout=10.0,
        )
        assert response.status_code == 404
