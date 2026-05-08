from fastapi import FastAPI
from pydantic import BaseModel

from app.core.config import settings
from app.routers.results import router as results_router


class HealthResponse(BaseModel):
    status: str
    service: str


app = FastAPI(
    title="TDSE Results Service",
    description="Tenant-aware REST API for querying handwriting emotion results.",
    version="0.1.0",
)

app.include_router(results_router)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", service=settings.service_name)
