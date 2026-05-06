import asyncio
import json
import logging
import threading
import time
from typing import Any

from app.core.config import settings
from app.core.messaging import (
    create_kafka_consumer,
    create_kafka_producer,
    publish_event,
)
from app.core.storage import download_from_s3, upload_to_s3
from app.pipeline import preprocess


logger = logging.getLogger(__name__)


class PreprocessingConsumer:
    def __init__(self) -> None:
        self._stop_event = threading.Event()
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    async def run(self) -> None:
        await asyncio.to_thread(self.run_forever)

    def stop(self) -> None:
        self._stop_event.set()

    def run_forever(self) -> None:
        self._running = True
        try:
            while not self._stop_event.is_set():
                consumer = None
                producer = None
                try:
                    consumer = create_kafka_consumer()
                    producer = create_kafka_producer()
                    logger.info(
                        "Listening to Kafka topic %s with group_id %s",
                        settings.kafka_topic_image_uploaded,
                        settings.kafka_group_id,
                    )
                    self._consume_messages(consumer=consumer, producer=producer)
                except Exception:
                    if not self._stop_event.is_set():
                        logger.exception("Kafka consumer loop failed; retrying")
                        time.sleep(settings.consumer_retry_seconds)
                finally:
                    self._close_resource(consumer)
                    self._close_resource(producer)
        finally:
            self._running = False

    def _consume_messages(self, consumer: Any, producer: Any) -> None:
        while not self._stop_event.is_set():
            message_batches = consumer.poll(
                timeout_ms=settings.kafka_poll_timeout_ms,
            )
            for messages in message_batches.values():
                for message in messages:
                    self._handle_message_safely(
                        raw_value=message.value,
                        consumer=consumer,
                        producer=producer,
                    )

    def _handle_message_safely(
        self,
        raw_value: Any,
        consumer: Any,
        producer: Any,
    ) -> None:
        try:
            payload = self._decode_payload(raw_value)
            self.process_upload_event(payload=payload, producer=producer)
        except Exception:
            logger.exception("Image preprocessing failed; skipping message")
        finally:
            try:
                consumer.commit()
            except Exception:
                logger.exception("Kafka offset commit failed")

    def process_upload_event(
        self,
        payload: dict[str, Any],
        producer: Any,
    ) -> None:
        image_id = str(payload["image_id"])
        tenant_id = str(payload["tenant_id"])
        user_id = str(payload["user_id"])
        s3_key_original = str(payload["s3_key"])

        original_image = download_from_s3(s3_key_original)
        processed_image = preprocess(original_image)
        s3_key_processed = build_processed_s3_key(s3_key_original)
        upload_to_s3(processed_image, s3_key_processed)

        publish_event(
            producer,
            settings.kafka_topic_image_preprocessed,
            {
                "image_id": image_id,
                "tenant_id": tenant_id,
                "user_id": user_id,
                "s3_key_processed": s3_key_processed,
                "s3_key_original": s3_key_original,
            },
        )

    def _decode_payload(self, raw_value: Any) -> dict[str, Any]:
        if isinstance(raw_value, dict):
            return raw_value
        if isinstance(raw_value, bytes):
            decoded_value = raw_value.decode("utf-8")
            payload = json.loads(decoded_value)
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


def build_processed_s3_key(original_key: str) -> str:
    if original_key.lower().endswith(".png"):
        return f"{original_key[:-4]}_processed.png"
    return f"{original_key}_processed.png"
