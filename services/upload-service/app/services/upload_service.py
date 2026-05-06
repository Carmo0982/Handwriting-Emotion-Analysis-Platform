from datetime import datetime, timezone
from typing import Literal, TypedDict
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile, status
from pydantic import BaseModel

from app.core.config import settings
from app.core.messaging import publish_event
from app.core.storage import upload_to_s3
from app.dependencies import AuthContext


ImageProcessingStatus = Literal["processing", "completed", "failed"]


class UploadResponse(BaseModel):
    image_id: UUID
    status: ImageProcessingStatus


class UploadStatusResponse(BaseModel):
    image_id: UUID
    status: ImageProcessingStatus


class ImageStatusRecord(TypedDict):
    tenant_id: UUID
    user_id: UUID
    status: ImageProcessingStatus


image_status_store: dict[UUID, ImageStatusRecord] = {}


class UploadService:
    async def upload_image(
        self,
        file: UploadFile,
        auth_context: AuthContext,
    ) -> UploadResponse:
        if file.content_type not in settings.allowed_content_types:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Only image/png and image/jpeg files are allowed",
            )

        file_bytes = await file.read(settings.max_upload_size_bytes + 1)
        if not file_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty",
            )
        if len(file_bytes) > settings.max_upload_size_bytes:
            raise HTTPException(
                status_code=413,
                detail="Uploaded file exceeds the 10MB limit",
            )

        image_id = uuid4()
        tenant_id = auth_context["tenant_id"]
        user_id = auth_context["user_id"]
        s3_key = f"{tenant_id}/{user_id}/{image_id}.png"

        try:
            uploaded_key = upload_to_s3(file_bytes, s3_key)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Image storage failed",
            ) from exc

        event_payload = {
            "image_id": str(image_id),
            "tenant_id": str(tenant_id),
            "user_id": str(user_id),
            "s3_key": uploaded_key,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            await publish_event(settings.kafka_topic_image_uploaded, event_payload)
        except Exception as exc:
            image_status_store[image_id] = {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "status": "failed",
            }
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Upload event publication failed",
            ) from exc

        image_status_store[image_id] = {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "status": "processing",
        }

        return UploadResponse(image_id=image_id, status="processing")

    def get_status(
        self,
        image_id: UUID,
        auth_context: AuthContext,
    ) -> UploadStatusResponse:
        record = image_status_store.get(image_id)
        if (
            record is None
            or record["tenant_id"] != auth_context["tenant_id"]
            or record["user_id"] != auth_context["user_id"]
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Image status not found",
            )

        return UploadStatusResponse(image_id=image_id, status=record["status"])


def set_image_status(image_id: UUID, image_status: ImageProcessingStatus) -> None:
    if image_id in image_status_store:
        image_status_store[image_id]["status"] = image_status


def clear_image_status_store() -> None:
    image_status_store.clear()
