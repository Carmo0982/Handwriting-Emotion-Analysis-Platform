import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel

from app.consumer import InferenceConsumer, is_model_available


logging.basicConfig(level=logging.INFO)

inference_consumer: Optional[InferenceConsumer] = None
consumer_task: Optional[asyncio.Task[None]] = None


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    global inference_consumer, consumer_task

    inference_consumer = InferenceConsumer()
    consumer_task = asyncio.create_task(asyncio.to_thread(inference_consumer.run_forever))
    try:
        yield
    finally:
        if inference_consumer is not None:
            inference_consumer.stop()
        if consumer_task is not None:
            try:
                await asyncio.wait_for(consumer_task, timeout=5)
            except asyncio.TimeoutError:
                consumer_task.cancel()


app = FastAPI(
    title="TDSE Inference Service",
    description="Kafka-driven handwriting emotion inference service for TDSE.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    model_loaded = (
        inference_consumer.is_model_loaded
        if inference_consumer is not None
        else is_model_available()
    )
    return HealthResponse(status="ok", model_loaded=model_loaded)
