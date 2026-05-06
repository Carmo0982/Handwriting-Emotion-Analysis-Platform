from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from app.core.config import settings
from app.core.database import init_db
from app.routers.auth import router as auth_router
from app.schemas.auth import HealthResponse


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    if settings.create_db_tables_on_startup:
        await init_db()
    yield


app = FastAPI(
    title="TDSE Auth Service",
    description="Authentication and tenant-aware identity service for TDSE.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(auth_router)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", service=settings.service_name)
