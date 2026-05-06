from typing import Annotated

from fastapi import APIRouter, Depends, status  # type: ignore[reportMissingImports]
from sqlalchemy.ext.asyncio import AsyncSession  # type: ignore[reportMissingImports]

from app.core.database import get_db_session
from app.dependencies import AuthContext, get_current_user
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.services.auth_service import AuthService


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    payload: RegisterRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserResponse:
    user = await AuthService(session).register_user(payload)
    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TokenResponse:
    return await AuthService(session).authenticate_user(payload)


@router.get("/me", response_model=UserResponse)
async def me(
    auth_context: Annotated[AuthContext, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserResponse:
    user = await AuthService(session).get_user_by_context(
        user_id=auth_context["user_id"],
        tenant_id=auth_context["tenant_id"],
    )
    return UserResponse.model_validate(user)
