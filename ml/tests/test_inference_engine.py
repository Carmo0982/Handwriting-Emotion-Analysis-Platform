from __future__ import annotations

from pathlib import Path

import pytest

from conftest import TinyInferenceModel
from ml.inference.engine import InferenceEngine
from ml.model import CLASS_NAMES


@pytest.fixture()
def engine(monkeypatch: pytest.MonkeyPatch, saved_model_path: Path) -> InferenceEngine:
    monkeypatch.setattr("ml.inference.engine.EmotionClassifier", TinyInferenceModel)
    return InferenceEngine(model_path=saved_model_path, device="cpu")


def test_engine_loads_model_from_checkpoint(engine: InferenceEngine) -> None:
    assert engine.model is not None


def test_engine_predict_returns_emotion_string(
    engine: InferenceEngine,
    white_image_bytes: bytes,
) -> None:
    prediction = engine.predict(white_image_bytes)

    assert isinstance(prediction["emotion"], str)


def test_engine_predict_emotion_is_valid_class(
    engine: InferenceEngine,
    white_image_bytes: bytes,
) -> None:
    prediction = engine.predict(white_image_bytes)

    assert prediction["emotion"] in CLASS_NAMES


def test_engine_predict_confidence_is_between_0_and_1(
    engine: InferenceEngine,
    white_image_bytes: bytes,
) -> None:
    prediction = engine.predict(white_image_bytes)

    assert 0.0 <= prediction["confidence"] <= 1.0


def test_engine_predict_scores_sum_to_approximately_1(
    engine: InferenceEngine,
    white_image_bytes: bytes,
) -> None:
    prediction = engine.predict(white_image_bytes)

    assert sum(prediction["scores"].values()) == pytest.approx(1.0, abs=1e-6)


def test_engine_predict_scores_has_all_4_classes(
    engine: InferenceEngine,
    white_image_bytes: bytes,
) -> None:
    prediction = engine.predict(white_image_bytes)

    assert set(prediction["scores"]) == set(CLASS_NAMES)


def test_engine_predict_with_white_image_does_not_raise(
    engine: InferenceEngine,
    white_image_bytes: bytes,
) -> None:
    prediction = engine.predict(white_image_bytes)

    assert prediction["emotion"] in CLASS_NAMES


def test_engine_predict_with_corrupt_bytes_raises_exception(
    engine: InferenceEngine,
    corrupt_bytes: bytes,
) -> None:
    with pytest.raises(ValueError, match="decode"):
        engine.predict(corrupt_bytes)


def test_engine_is_deterministic_in_eval_mode(
    engine: InferenceEngine,
    white_image_bytes: bytes,
) -> None:
    first_prediction = engine.predict(white_image_bytes)
    second_prediction = engine.predict(white_image_bytes)

    assert first_prediction == second_prediction


def test_engine_works_on_cpu_without_gpu(engine: InferenceEngine) -> None:
    assert engine.device.type == "cpu"
    assert next(engine.model.parameters()).device.type == "cpu"
