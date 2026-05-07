from __future__ import annotations

import json
import logging
import random
import threading
import time
from pathlib import Path
from typing import Any, Protocol

from kafka import KafkaConsumer

from app.core.config import settings
from app.core.results_store import save_result
from app.core.storage import download_from_s3


logger = logging.getLogger(__name__)

CLASS_NAMES: tuple[str, str, str, str] = (
    "neutral",
    "anxiety",
    "stress",
    "depression",
)


class PredictionEngine(Protocol):
    def predict(self, image_bytes: bytes) -> dict[str, Any]:
        ...


class DummyInferenceEngine:
    def predict(self, image_bytes: bytes) -> dict[str, Any]:
        del image_bytes

        raw_scores = [random.random() for _ in CLASS_NAMES]
        total = sum(raw_scores) or 1.0
        probabilities = [score / total for score in raw_scores]
        scores = {
            class_name: probabilities[index]
            for index, class_name in enumerate(CLASS_NAMES)
        }
        emotion = max(scores, key=scores.get)
        return {
            "emotion": emotion,
            "confidence": scores[emotion],
            "scores": scores,
        }


class InferenceConsumer:
    def __init__(self, engine: PredictionEngine | None = None) -> None:
        self.engine = engine or load_inference_engine()
        self._stop_event = threading.Event()
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def is_model_loaded(self) -> bool:
        return self.engine is not None

    def stop(self) -> None:
        self._stop_event.set()

    def run_forever(self) -> None:
        self._running = True
        try:
            while not self._stop_event.is_set():
                consumer = None
                try:
                    consumer = self._create_kafka_consumer()
                    logger.info(
                        "Listening to Kafka topic %s with group_id %s",
                        settings.kafka_topic_image_preprocessed,
                        settings.kafka_group_id,
                    )
                    self._consume_messages(consumer)
                except Exception:
                    if not self._stop_event.is_set():
                        logger.exception("Kafka inference loop failed; retrying")
                        time.sleep(settings.consumer_retry_seconds)
                finally:
                    self._close_resource(consumer)
        finally:
            self._running = False

    def process_preprocessed_event(self, payload: dict[str, Any]) -> None:
        image_id = str(payload["image_id"])
        tenant_id = str(payload["tenant_id"])
        user_id = str(payload["user_id"])
        s3_key_processed = str(payload["s3_key_processed"])

        try:
            image_bytes = download_from_s3(s3_key_processed)
            prediction = self.engine.predict(image_bytes)
            prediction["status"] = "completed"
        except Exception as exc:
            logger.exception("Model inference failed for image_id=%s", image_id)
            prediction = {
                "emotion": "unknown",
                "confidence": 0.0,
                "scores": {},
                "status": "failed",
                "error": str(exc),
            }

        save_result(
            image_id=image_id,
            tenant_id=tenant_id,
            user_id=user_id,
            prediction=prediction,
        )

    def _create_kafka_consumer(self) -> KafkaConsumer:
        return KafkaConsumer(
            settings.kafka_topic_image_preprocessed,
            bootstrap_servers=settings.kafka_bootstrap_servers_list,
            group_id=settings.kafka_group_id,
            enable_auto_commit=False,
            auto_offset_reset=settings.kafka_auto_offset_reset,
            max_poll_records=settings.kafka_max_poll_records,
        )

    def _consume_messages(self, consumer: KafkaConsumer) -> None:
        while not self._stop_event.is_set():
            message_batches = consumer.poll(
                timeout_ms=settings.kafka_poll_timeout_ms,
            )
            for messages in message_batches.values():
                for message in messages:
                    self._handle_message_safely(
                        raw_value=message.value,
                        consumer=consumer,
                    )

    def _handle_message_safely(
        self,
        raw_value: Any,
        consumer: KafkaConsumer,
    ) -> None:
        try:
            payload = self._decode_payload(raw_value)
            self.process_preprocessed_event(payload)
        except Exception:
            logger.exception("Inference event handling failed; skipping message")
        finally:
            try:
                consumer.commit()
            except Exception:
                logger.exception("Kafka offset commit failed")

    def _decode_payload(self, raw_value: Any) -> dict[str, Any]:
        if isinstance(raw_value, dict):
            return raw_value
        if isinstance(raw_value, bytes):
            payload = json.loads(raw_value.decode("utf-8"))
        elif isinstance(raw_value, str):
            payload = json.loads(raw_value)
        else:
            raise ValueError("Unsupported Kafka message value")

        if not isinstance(payload, dict):
            raise ValueError("Kafka message payload must be a JSON object")
        return payload

    def _close_resource(self, resource: Any) -> None:
        if resource is None:
            return
        try:
            resource.close()
        except Exception:
            logger.exception("Failed to close Kafka resource")


def load_inference_engine() -> PredictionEngine:
    model_path = Path(settings.model_path)
    if model_path.exists():
        from ml.inference.engine import InferenceEngine

        logger.info("Loading inference model from %s", model_path)
        return InferenceEngine(model_path=model_path, device=settings.device)

    if settings.use_dummy_model_if_missing:
        logger.warning(
            "MODEL_PATH %s does not exist; using dummy inference engine",
            model_path,
        )
        return DummyInferenceEngine()

    raise FileNotFoundError(f"MODEL_PATH does not exist: {model_path}")


def is_model_available() -> bool:
    return settings.model_file_exists or settings.use_dummy_model_if_missing
