import cv2
import numpy as np


def preprocess(image_bytes: bytes) -> bytes:
    image_buffer = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(image_buffer, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Could not decode image bytes")

    grayscale = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    denoised = cv2.GaussianBlur(grayscale, (3, 3), 0)
    binary = cv2.adaptiveThreshold(
        denoised,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        11,
        2,
    )
    resized = cv2.resize(binary, (224, 224), interpolation=cv2.INTER_AREA)
    normalized = resized.astype(np.float32) / 255.0

    png_ready = np.clip(normalized * 255.0, 0, 255).astype(np.uint8)
    encoded_successfully, encoded_image = cv2.imencode(".png", png_ready)
    if not encoded_successfully:
        raise ValueError("Could not encode preprocessed image as PNG")

    return encoded_image.tobytes()
