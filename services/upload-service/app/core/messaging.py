import json
from typing import Any

from app.core.config import settings


async def publish_event(topic: str, payload: dict[str, Any]) -> None:
    from aiokafka import AIOKafkaProducer

    producer = AIOKafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        security_protocol=settings.kafka_security_protocol,
        value_serializer=lambda value: json.dumps(value).encode("utf-8"),
    )
    await producer.start()
    try:
        await producer.send_and_wait(topic, payload)
    finally:
        await producer.stop()
