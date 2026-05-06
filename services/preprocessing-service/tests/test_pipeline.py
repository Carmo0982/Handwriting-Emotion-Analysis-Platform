from io import BytesIO

import cv2
import numpy as np
import pytest
from PIL import Image

from app.pipeline import preprocess


def make_synthetic_image_bytes(extension: str = ".png") -> bytes:
    image = np.full((180, 320, 3), 255, dtype=np.uint8)
    image[40:48, 40:280] = 0
    image[72:80, 60:260] = 0
    image[104:112, 30:290] = 0
    image[135:142, 80:240] = 0

    encoded_successfully, encoded_image = cv2.imencode(extension, image)
    assert encoded_successfully
    return encoded_image.tobytes()


def test_preprocess_returns_224_png_bytes() -> None:
    processed_bytes = preprocess(make_synthetic_image_bytes())

    with Image.open(BytesIO(processed_bytes)) as image:
        assert image.format == "PNG"
        assert image.size == (224, 224)
        assert image.mode == "L"


def test_preprocess_outputs_decodable_uint8_image() -> None:
    processed_bytes = preprocess(make_synthetic_image_bytes(".jpg"))
    decoded_image = cv2.imdecode(
        np.frombuffer(processed_bytes, dtype=np.uint8),
        cv2.IMREAD_UNCHANGED,
    )

    assert decoded_image is not None
    assert decoded_image.shape == (224, 224)
    assert decoded_image.dtype == np.uint8
    assert decoded_image.min() >= 0
    assert decoded_image.max() <= 255


def test_preprocess_rejects_corrupt_image_bytes() -> None:
    with pytest.raises(ValueError, match="decode"):
        preprocess(b"not-a-valid-image")
