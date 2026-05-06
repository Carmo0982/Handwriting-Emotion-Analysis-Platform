from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.user import Tenant, User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def register_user(self, payload: RegisterRequest) -> User:
        tenant = await self.session.get(Tenant, payload.tenant_id)
        if tenant is None or not tenant.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found or inactive",
            )

        normalized_email = str(payload.email).lower()
        existing_user = await self.session.scalar(
            select(User).where(func.lower(User.email) == normalized_email)
        )
        if existing_user is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email is already registered",
            )

        user = User(
            tenant_id=payload.tenant_id,
            email=normalized_email,
            hashed_password=get_password_hash(payload.password),
            is_active=True,
        )
        self.session.add(user)

        try:
            await self.session.commit()
            await self.session.refresh(user)
        except IntegrityError as exc:
            await self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email is already registered",
            ) from exc

        return user

    async def authenticate_user(self, payload: LoginRequest) -> TokenResponse:
        user = await self._get_user_by_email(str(payload.email).lower())
        if user is None or not verify_password(payload.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        tenant = await self.session.get(Tenant, user.tenant_id)
        if not user.is_active or tenant is None or not tenant.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User or tenant is inactive",
            )

        access_token = create_access_token(subject=user.id, tenant_id=user.tenant_id)
        return TokenResponse(access_token=access_token)

    async def get_user_by_context(self, user_id: UUID, tenant_id: UUID) -> User:
        user = await self.session.scalar(
            select(User).where(User.id == user_id, User.tenant_id == tenant_id)
        )
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authenticated user not found or inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user

    async def _get_user_by_email(self, email: str) -> Optional[User]:
        statement: Select[tuple[User]] = select(User).where(
            func.lower(User.email) == email
        )
        return await self.session.scalar(statement)
