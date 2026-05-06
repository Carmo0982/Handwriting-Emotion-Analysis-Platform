from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile, status

from app.dependencies import AuthContext, get_current_user
from app.services.upload_service import (
    UploadResponse,
    UploadService,
    UploadStatusResponse,
)


router = APIRouter(tags=["upload"])


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_image(
    auth_context: Annotated[AuthContext, Depends(get_current_user)],
    file: Annotated[UploadFile, File(...)],
) -> UploadResponse:
    return await UploadService().upload_image(file=file, auth_context=auth_context)


@router.get("/upload/{image_id}/status", response_model=UploadStatusResponse)
async def get_upload_status(
    image_id: UUID,
    auth_context: Annotated[AuthContext, Depends(get_current_user)],
) -> UploadStatusResponse:
    return UploadService().get_status(image_id=image_id, auth_context=auth_context)
