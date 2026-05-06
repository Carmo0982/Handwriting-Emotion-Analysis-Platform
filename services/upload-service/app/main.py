from fastapi import FastAPI
from pydantic import BaseModel

from app.core.config import settings
from app.routers.upload import router as upload_router


class HealthResponse(BaseModel):
    status: str
    service: str


app = FastAPI(
    title="TDSE Upload Service",
    description="Tenant-aware handwriting image ingestion service for TDSE.",
    version="0.1.0",
)

app.include_router(upload_router)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", service=settings.service_name)
