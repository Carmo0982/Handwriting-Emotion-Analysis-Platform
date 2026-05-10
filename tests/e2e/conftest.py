from __future__ import annotations

import asyncio
import os
import subprocess
import time
from collections.abc import Callable, Generator
from pathlib import Path
from typing import Any, TypedDict
from uuid import uuid4

import httpx
import pytest


AUTH_URL = os.getenv("AUTH_URL", "http://localhost:8001").rstrip("/")
UPLOAD_URL = os.getenv("UPLOAD_URL", "http://localhost:8002").rstrip("/")
PREPROCESSING_URL = os.getenv(
    "PREPROCESSING_URL", "http://localhost:8003"
).rstrip("/")
INFERENCE_URL = os.getenv("INFERENCE_URL", "http://localhost:8004").rstrip("/")
RESULTS_URL = os.getenv("RESULTS_URL", "http://localhost:8005").rstrip("/")

TEST_TENANT_A_ID = os.getenv("TEST_TENANT_A_ID")
TEST_TENANT_B_ID = os.getenv("TEST_TENANT_B_ID")

TEST_PASSWORD = "E2e-test-password-123!"
EMAIL_DOMAIN = "example.com"
EMAIL_PREFIX = "tdse-e2e"
VALID_EMOTIONS = {"neutral", "anxiety", "stress", "depression"}


class AuthenticatedUser(TypedDict):
    email: str
    password: str
    token: str
    headers: dict[str, str]
    tenant_id: str


@pytest.fixture(scope="session", autouse=True)
def require_e2e_environment() -> Generator[None, None, None]:
    missing_vars = [
        name
        for name, value in {
            "TEST_TENANT_A_ID": TEST_TENANT_A_ID,
            "TEST_TENANT_B_ID": TEST_TENANT_B_ID,
        }.items()
        if not value
    ]
    if missing_vars:
        pytest.skip(
            "E2E tests require docker compose and env vars: "
            + ", ".join(missing_vars)
        )

    unreachable = _wait_for_services()
    if unreachable:
        pytest.skip(
            "E2E services did not respond within 10s: "
            + ", ".join(sorted(unreachable))
        )

    yield

    _cleanup_test_users()


@pytest.fixture()
def create_user() -> Callable[[str, str, str], dict[str, Any]]:
    def _create_user(email: str, password: str, tenant_id: str) -> dict[str, Any]:
        response = httpx.post(
            f"{AUTH_URL}/auth/register",
            json={"email": email, "password": password, "tenant_id": tenant_id},
            timeout=10.0,
        )
        assert response.status_code == 201, response.text
        return response.json()

    return _create_user


@pytest.fixture()
def login() -> Callable[[str, str], str]:
    def _login(email: str, password: str) -> str:
        response = httpx.post(
            f"{AUTH_URL}/auth/login",
            json={"email": email, "password": password},
            timeout=10.0,
        )
        assert response.status_code == 200, response.text
        token = response.json()["access_token"]
        assert token
        return str(token)

    return _login


@pytest.fixture()
def upload_image() -> Callable[[str, Path], str]:
    def _upload_image(token: str, image_path: Path) -> str:
        with image_path.open("rb") as image_file:
            response = httpx.post(
                f"{UPLOAD_URL}/upload",
                headers=_auth_headers(token),
                files={"file": ("handwriting.png", image_file, "image/png")},
                timeout=20.0,
            )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["status"] == "processing"
        assert payload["image_id"]
        return str(payload["image_id"])

    return _upload_image


@pytest.fixture()
def wait_for_result() -> Callable[[str, str, int], dict[str, Any]]:
    def _wait_for_result(
        image_id: str,
        token: str,
        timeout: int = 30,
    ) -> dict[str, Any]:
        deadline = time.monotonic() + timeout
        last_response_text = ""

        while time.monotonic() < deadline:
            response = httpx.get(
                f"{RESULTS_URL}/results/{image_id}",
                headers=_auth_headers(token),
                timeout=10.0,
            )
            if response.status_code == 200:
                payload = response.json()
                if payload["status"] == "completed":
                    return payload
                if payload["status"] == "failed":
                    pytest.fail(f"Inference failed for image {image_id}: {payload}")
            elif response.status_code != 404:
                last_response_text = response.text
            time.sleep(1.0)

        pytest.fail(
            f"Timed out waiting for result {image_id}. Last response: "
            f"{last_response_text or 'not found'}"
        )

    return _wait_for_result


@pytest.fixture()
def sample_handwriting_image(tmp_path: Path) -> Path:
    cv2 = pytest.importorskip("cv2")
    np = pytest.importorskip("numpy")

    image = np.ones((300, 300), dtype=np.uint8) * 255
    cv2.line(image, (45, 90), (255, 90), 0, 2)
    cv2.line(image, (55, 135), (240, 145), 0, 2)
    cv2.line(image, (40, 190), (260, 175), 0, 2)
    cv2.putText(
        image,
        "tdse",
        (70, 245),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        0,
        2,
        cv2.LINE_AA,
    )

    image_path = tmp_path / "sample-handwriting.png"
    ok = cv2.imwrite(str(image_path), image)
    assert ok
    return image_path


@pytest.fixture()
def user_tenant_a(
    create_user: Callable[[str, str, str], dict[str, Any]],
    login: Callable[[str, str], str],
) -> AuthenticatedUser:
    assert TEST_TENANT_A_ID is not None
    return _create_authenticated_user(create_user, login, TEST_TENANT_A_ID)


@pytest.fixture()
def user_tenant_b(
    create_user: Callable[[str, str, str], dict[str, Any]],
    login: Callable[[str, str], str],
) -> AuthenticatedUser:
    assert TEST_TENANT_B_ID is not None
    return _create_authenticated_user(create_user, login, TEST_TENANT_B_ID)


def make_test_email(label: str = "user") -> str:
    return f"{EMAIL_PREFIX}-{label}-{uuid4().hex}@{EMAIL_DOMAIN}"


def service_urls() -> dict[str, str]:
    return {
        "auth": AUTH_URL,
        "upload": UPLOAD_URL,
        "preprocessing": PREPROCESSING_URL,
        "inference": INFERENCE_URL,
        "results": RESULTS_URL,
    }


def assert_valid_result_payload(payload: dict[str, Any]) -> None:
    assert payload["emotion"] in VALID_EMOTIONS
    assert 0.0 <= payload["confidence"] <= 1.0
    assert set(payload["scores"]) == VALID_EMOTIONS
    assert all(0.0 <= float(score) <= 1.0 for score in payload["scores"].values())
    assert payload["status"] == "completed"
    assert payload["created_at"]


async def async_upload_image(token: str, image_path: Path) -> str:
    async with httpx.AsyncClient(timeout=20.0) as client:
        with image_path.open("rb") as image_file:
            response = await client.post(
                f"{UPLOAD_URL}/upload",
                headers=_auth_headers(token),
                files={"file": ("handwriting.png", image_file, "image/png")},
            )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "processing"
    return str(payload["image_id"])


async def async_wait_for_result(
    image_id: str,
    token: str,
    timeout: int = 45,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    async with httpx.AsyncClient(timeout=10.0) as client:
        while time.monotonic() < deadline:
            response = await client.get(
                f"{RESULTS_URL}/results/{image_id}",
                headers=_auth_headers(token),
            )
            if response.status_code == 200:
                payload = response.json()
                if payload["status"] == "completed":
                    return payload
                if payload["status"] == "failed":
                    raise AssertionError(f"Inference failed for {image_id}: {payload}")
            elif response.status_code != 404:
                raise AssertionError(
                    f"Unexpected result lookup response: {response.status_code} "
                    f"{response.text}"
                )
            await asyncio.sleep(1.0)

    raise AssertionError(f"Timed out waiting for result {image_id}")


def _create_authenticated_user(
    create_user: Callable[[str, str, str], dict[str, Any]],
    login: Callable[[str, str], str],
    tenant_id: str,
) -> AuthenticatedUser:
    email = make_test_email("tenant")
    create_user(email, TEST_PASSWORD, tenant_id)
    token = login(email, TEST_PASSWORD)
    return {
        "email": email,
        "password": TEST_PASSWORD,
        "token": token,
        "headers": _auth_headers(token),
        "tenant_id": tenant_id,
    }


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _wait_for_services(timeout: float = 10.0) -> set[str]:
    pending = set(service_urls())
    deadline = time.monotonic() + timeout

    while pending and time.monotonic() < deadline:
        for service_name in list(pending):
            try:
                response = httpx.get(
                    f"{service_urls()[service_name]}/health",
                    timeout=2.0,
                )
                if response.status_code == 200:
                    pending.remove(service_name)
            except httpx.HTTPError:
                pass
        if pending:
            time.sleep(0.5)

    return pending


def _cleanup_test_users() -> None:
    command = [
        "docker",
        "compose",
        "exec",
        "-T",
        "postgres",
        "psql",
        "-U",
        os.getenv("POSTGRES_USER", "user"),
        "-d",
        os.getenv("POSTGRES_DB", "tdse"),
        "-c",
        f"DELETE FROM users WHERE email LIKE '{EMAIL_PREFIX}-%@{EMAIL_DOMAIN}';",
    ]
    try:
        subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=15.0,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        pass
