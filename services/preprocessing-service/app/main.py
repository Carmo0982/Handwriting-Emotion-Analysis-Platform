import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel

from app.consumer import PreprocessingConsumer


logging.basicConfig(level=logging.INFO)

preprocessing_consumer = PreprocessingConsumer()
consumer_task: Optional[asyncio.Task[None]] = None


class HealthResponse(BaseModel):
    status: str
    consumer: str


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    global consumer_task

    consumer_task = asyncio.create_task(preprocessing_consumer.run())
    try:
        yield
    finally:
        preprocessing_consumer.stop()
        if consumer_task is not None:
            try:
                await asyncio.wait_for(consumer_task, timeout=5)
            except asyncio.TimeoutError:
                consumer_task.cancel()


app = FastAPI(
    title="TDSE Preprocessing Service",
    description="Kafka-driven handwriting image preprocessing service for TDSE.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", consumer="running")
