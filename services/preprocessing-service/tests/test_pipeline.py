from __future__ import annotations

from io import BytesIO

import cv2
import numpy as np
import pytest
from PIL import Image

from app.pipeline import preprocess
from conftest import decode_grayscale_png, encode_grayscale_png


def test_preprocess_returns_bytes(handwriting_image_bytes: bytes) -> None:
    processed_bytes = preprocess(handwriting_image_bytes)

    assert isinstance(processed_bytes, bytes)
    assert len(processed_bytes) > 0


def test_preprocess_output_is_valid_png(handwriting_image_bytes: bytes) -> None:
    processed_bytes = preprocess(handwriting_image_bytes)

    with Image.open(BytesIO(processed_bytes)) as image:
        assert image.format == "PNG"


def test_preprocess_output_dimensions_are_224x224(handwriting_image_bytes: bytes) -> None:
    processed_bytes = preprocess(handwriting_image_bytes)
    decoded_image = decode_grayscale_png(processed_bytes)

    assert decoded_image.shape == (224, 224)


def test_preprocess_white_image_does_not_raise(white_image_bytes: bytes) -> None:
    processed_bytes = preprocess(white_image_bytes)

    assert len(processed_bytes) > 0


def test_preprocess_black_image_does_not_raise(black_image_bytes: bytes) -> None:
    processed_bytes = preprocess(black_image_bytes)

    assert len(processed_bytes) > 0


def test_preprocess_handwriting_image_does_not_raise(
    handwriting_image_bytes: bytes,
) -> None:
    processed_bytes = preprocess(handwriting_image_bytes)

    assert len(processed_bytes) > 0


def test_preprocess_output_values_are_normalized_between_0_and_1(
    handwriting_image_bytes: bytes,
) -> None:
    processed_bytes = preprocess(handwriting_image_bytes)
    decoded_image = decode_grayscale_png(processed_bytes)
    normalized_image = decoded_image.astype(np.float32) / 255.0

    assert normalized_image.min() >= 0.0
    assert normalized_image.max() <= 1.0


def test_preprocess_corrupt_bytes_raises_controlled_exception(
    corrupt_bytes: bytes,
) -> None:
    with pytest.raises(ValueError, match="decode"):
        preprocess(corrupt_bytes)


def test_preprocess_very_small_image_resizes_correctly() -> None:
    image = np.ones((8, 8), dtype=np.uint8) * 255

    processed_bytes = preprocess(encode_grayscale_png(image))
    decoded_image = decode_grayscale_png(processed_bytes)

    assert decoded_image.shape == (224, 224)


def test_preprocess_very_large_image_resizes_correctly() -> None:
    image = np.ones((1800, 1800), dtype=np.uint8) * 255
    cv2.line(image, (100, 900), (1700, 900), 0, 8)

    processed_bytes = preprocess(encode_grayscale_png(image))
    decoded_image = decode_grayscale_png(processed_bytes)

    assert decoded_image.shape == (224, 224)


def test_preprocess_removes_noise(noise_image_bytes: bytes) -> None:
    noisy_input = decode_grayscale_png(noise_image_bytes)

    processed_bytes = preprocess(noise_image_bytes)
    processed_output = decode_grayscale_png(processed_bytes)

    assert processed_output.var() < noisy_input.var()


def test_preprocess_is_deterministic(handwriting_image_bytes: bytes) -> None:
    first_output = preprocess(handwriting_image_bytes)
    second_output = preprocess(handwriting_image_bytes)

    assert first_output == second_output
