import json
from typing import Any

from app.core.config import settings


def create_kafka_consumer() -> Any:
    from kafka import KafkaConsumer

    return KafkaConsumer(
        settings.kafka_topic_image_uploaded,
        bootstrap_servers=settings.kafka_bootstrap_servers_list,
        group_id=settings.kafka_group_id,
        enable_auto_commit=False,
        auto_offset_reset=settings.kafka_auto_offset_reset,
        max_poll_records=settings.kafka_max_poll_records,
    )


def create_kafka_producer() -> Any:
    from kafka import KafkaProducer

    return KafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers_list,
        value_serializer=lambda value: json.dumps(value).encode("utf-8"),
    )


def publish_event(producer: Any, topic: str, payload: dict[str, Any]) -> None:
    producer.send(topic, payload)
    producer.flush()
