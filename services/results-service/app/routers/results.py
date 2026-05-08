from __future__ import annotations

from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.dependencies import AuthContext, get_current_user
from app.services.results_service import EMOTION_CLASSES, ResultsService


router = APIRouter(prefix="/results", tags=["results"])


class ResultResponse(BaseModel):
    image_id: str
    emotion: str
    confidence: float
    scores: dict[str, float]
    status: str
    created_at: str


class SummaryResponse(BaseModel):
    total_analyses: int
    emotion_distribution: dict[str, float]
    last_analysis_date: Optional[str]


@router.get("/summary", response_model=SummaryResponse)
async def get_results_summary(
    auth_context: Annotated[AuthContext, Depends(get_current_user)],
) -> SummaryResponse:
    summary = ResultsService().summarize_results(
        tenant_id=auth_context["tenant_id"],
        user_id=auth_context["user_id"],
    )
    return SummaryResponse.model_validate(summary)


@router.get("", response_model=list[ResultResponse])
async def list_results(
    auth_context: Annotated[AuthContext, Depends(get_current_user)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    emotion: Annotated[
        Optional[str],
        Query(pattern=f"^({'|'.join(EMOTION_CLASSES)})$"),
    ] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> list[ResultResponse]:
    results = ResultsService().list_results(
        tenant_id=auth_context["tenant_id"],
        user_id=auth_context["user_id"],
        limit=limit,
        emotion=emotion,
        date_from=date_from,
        date_to=date_to,
    )
    return [ResultResponse.model_validate(result) for result in results]


@router.get("/{image_id}", response_model=ResultResponse)
async def get_result(
    image_id: str,
    auth_context: Annotated[AuthContext, Depends(get_current_user)],
) -> ResultResponse:
    result = ResultsService().get_result(
        image_id=image_id,
        tenant_id=auth_context["tenant_id"],
    )
    return ResultResponse.model_validate(result)
