from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordBearer

from ..core.security import decode_token
from ..core.acr_engine import get_row_level_condition, get_user_acr_context
from ..models import store

security_scheme = HTTPBearer(auto_error=False)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(security_scheme),
) -> dict:
    if creds is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    token = creds.credentials
    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
    if await store.is_token_blacklisted(payload.get("jti", "")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked")
    user = await store.get_user_by_id(payload["sub"])
    if user is None or not user.get("is_active"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive or not found")
    return user


async def get_current_admin(user: dict = Depends(get_current_user)) -> dict:
    if "admin" not in user.get("roles", []):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")
    return user


async def get_acr_context(user: dict = Depends(get_current_user)) -> dict:
    """Get ACR context for the current user — usable by any route that needs row-level security."""
    return await get_user_acr_context(user)


async def get_row_level_filter(
    resource_type: str,
    user: dict = Depends(get_current_user),
) -> tuple[str, list]:
    """Get a WHERE clause fragment that applies row-level security for the given resource type."""
    return await get_row_level_condition(user, resource_type)
