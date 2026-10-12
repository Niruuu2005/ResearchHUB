import logging
from typing import Optional
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.db.session import get_db
from app.models.database import User
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)


def extract_session_token(request: Request) -> Optional[str]:
    """Extract session token from Authorization header or HttpOnly cookie."""
    # 1. Bearer token in Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1].strip()
        if token:
            return token

    # 2. HttpOnly Cookie
    cookie_token = request.cookies.get(settings.session_cookie_name)
    if cookie_token:
        return cookie_token.strip()

    return None


async def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """
    Primary authentication dependency.
    Validates application session token, resolves User from database,
    and rejects unauthenticated or expired requests with HTTP 401.
    """
    token = extract_session_token(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please sign in with Google.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = AuthService.get_user_from_session_token(db, token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_optional_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Optional authentication dependency for endpoints supporting both anonymous and authenticated usage."""
    token = extract_session_token(request)
    if not token:
        return None
    return AuthService.get_user_from_session_token(db, token)
