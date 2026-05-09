from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from fastapi import HTTPException, status

from app.core.dynamo import get_result_by_id, get_results_by_user


EMOTION_CLASSES: tuple[str, str, str, str] = (
    "neutral",
    "anxiety",
    "stress",
    "depression",
)


class ResultsService:
    def get_result(
        self,
        image_id: str,
        tenant_id: UUID,
        user_id: UUID,
    ) -> dict[str, Any]:
        result = get_result_by_id(image_id=image_id, tenant_id=str(tenant_id))
        if result is None or str(result.get("user_id")) != str(user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Result not found",
            )
        return self._public_result(result)

    def list_results(
        self,
        tenant_id: UUID,
        user_id: UUID,
        limit: int,
        emotion: Optional[str],
        date_from: Optional[datetime],
        date_to: Optional[datetime],
    ) -> list[dict[str, Any]]:
        filters = {
            "limit": limit,
            "emotion": emotion,
            "date_from": date_from.isoformat() if date_from else None,
            "date_to": date_to.isoformat() if date_to else None,
        }
        results = get_results_by_user(
            tenant_id=str(tenant_id),
            user_id=str(user_id),
            filters=filters,
        )
        return [self._public_result(result) for result in results]

    def summarize_results(self, tenant_id: UUID, user_id: UUID) -> dict[str, Any]:
        results = get_results_by_user(
            tenant_id=str(tenant_id),
            user_id=str(user_id),
            filters={"limit": None},
        )
        total_analyses = len(results)
        distribution = {emotion: 0.0 for emotion in EMOTION_CLASSES}

        if total_analyses > 0:
            for result in results:
                emotion = str(result.get("emotion", ""))
                if emotion in distribution:
                    distribution[emotion] += 1.0
            distribution = {
                emotion: round((count / total_analyses) * 100, 2)
                for emotion, count in distribution.items()
            }

        last_analysis_date = None
        if results:
            last_analysis_date = max(str(result.get("created_at", "")) for result in results)

        return {
            "total_analyses": total_analyses,
            "emotion_distribution": distribution,
            "last_analysis_date": last_analysis_date,
        }

    def _public_result(self, result: dict[str, Any]) -> dict[str, Any]:
        return {
            "image_id": str(result.get("image_id", "")),
            "emotion": str(result.get("emotion", "unknown")),
            "confidence": float(result.get("confidence", 0.0)),
            "scores": {
                str(key): float(value)
                for key, value in dict(result.get("scores", {})).items()
            },
            "status": str(result.get("status", "unknown")),
            "created_at": str(result.get("created_at", "")),
        }
