#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import struct
import time
import urllib.error
import urllib.request
import uuid
import zlib


AUTH_URL = os.getenv("AUTH_URL", "http://localhost:8001")
UPLOAD_URL = os.getenv("UPLOAD_URL", "http://localhost:8002")
RESULTS_URL = os.getenv("RESULTS_URL", "http://localhost:8005")
TENANT_ID = os.getenv("TENANT_ID", "11111111-1111-1111-1111-111111111111")
PASSWORD = os.getenv("TDSE_TEST_PASSWORD", "StrongPass123")


def main() -> None:
    email = f"local-{int(time.time())}@tdse.local"
    print(f"Registering user: {email}")
    request_json(
        f"{AUTH_URL}/auth/register",
        {
            "email": email,
            "password": PASSWORD,
            "tenant_id": TENANT_ID,
        },
    )

    token_response = request_json(
        f"{AUTH_URL}/auth/login",
        {
            "email": email,
            "password": PASSWORD,
        },
    )
    token = token_response["access_token"]
    print("JWT acquired")

    upload_response = upload_png(token=token, image_bytes=make_handwriting_png())
    image_id = upload_response["image_id"]
    print(f"Image accepted: {image_id}")

    result = wait_for_result(token=token, image_id=image_id)
    print(json.dumps(result, indent=2, sort_keys=True))


def request_json(url: str, payload: dict[str, object]) -> dict[str, object]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    return read_json(request)


def upload_png(token: str, image_bytes: bytes) -> dict[str, object]:
    boundary = f"----TDSEBoundary{uuid.uuid4().hex}"
    body = b"".join(
        [
            f"--{boundary}\r\n".encode("utf-8"),
            b'Content-Disposition: form-data; name="file"; filename="sample.png"\r\n',
            b"Content-Type: image/png\r\n\r\n",
            image_bytes,
            b"\r\n",
            f"--{boundary}--\r\n".encode("utf-8"),
        ]
    )
    request = urllib.request.Request(
        f"{UPLOAD_URL}/upload",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    return read_json(request)


def wait_for_result(token: str, image_id: str, timeout_seconds: int = 90) -> dict[str, object]:
    deadline = time.time() + timeout_seconds
    request = urllib.request.Request(
        f"{RESULTS_URL}/results/{image_id}",
        headers={"Authorization": f"Bearer {token}"},
        method="GET",
    )

    while time.time() < deadline:
        try:
            return read_json(request)
        except urllib.error.HTTPError as exc:
            if exc.code != 404:
                raise
            time.sleep(3)

    raise TimeoutError(f"Timed out waiting for result {image_id}")


def read_json(request: urllib.request.Request) -> dict[str, object]:
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8")
        raise RuntimeError(f"{request.full_url} failed: {exc.code} {error_body}") from exc


def make_handwriting_png(width: int = 224, height: int = 224) -> bytes:
    pixels = bytearray([255] * (width * height))
    for y in (54, 92, 130, 168):
        for row in range(y, min(y + 4, height)):
            for x in range(32, 190):
                if (x + row) % 9 != 0:
                    pixels[row * width + x] = 20

    raw_rows = bytearray()
    for y in range(height):
        raw_rows.append(0)
        start = y * width
        raw_rows.extend(pixels[start : start + width])

    return b"".join(
        [
            b"\x89PNG\r\n\x1a\n",
            png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)),
            png_chunk(b"IDAT", zlib.compress(bytes(raw_rows), level=9)),
            png_chunk(b"IEND", b""),
        ]
    )


def png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    checksum = zlib.crc32(chunk_type)
    checksum = zlib.crc32(data, checksum)
    return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", checksum)


if __name__ == "__main__":
    main()
