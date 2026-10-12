import hashlib
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.db.session import get_db
from app.models.database import User
from app.models.schemas import AuthStatusResponse, MockLoginRequest, UserOut
from app.services.auth_service import AuthService
from app.api.dependencies import get_current_user, get_optional_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Google Authentication & Sessions"])
auth_service = AuthService()

OAUTH_STATE_COOKIE = "rh_oauth_state"


@router.get("/google/login", summary="Start Google Sign-In")
async def google_login(
    mock: Optional[bool] = Query(default=False, description="Use developer mock login flow if true"),
    next_url: Optional[str] = Query(default="/", description="URL to redirect to after successful sign-in"),
):
    """
    Initiates Google OpenID Connect authorization-code flow with PKCE, state CSRF protection,
    and nonce replay validation.
    """
    # 1. Dev / Mock flow when Google credentials are not configured or mock is explicitly requested
    if (not settings.google_client_id or mock) and settings.allow_mock_auth:
        logger.info("Starting mock authentication flow for development/testing.")
        redirect = RedirectResponse(url=f"/#mock-login?next={next_url or '/'}", status_code=status.HTTP_302_FOUND)
        return redirect

    if not settings.google_client_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google OAuth is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET or enable ALLOW_MOCK_AUTH=true.",
        )

    # 2. Production Google OpenID Connect flow
    code_verifier, code_challenge = auth_service.generate_pkce_pair()
    state, nonce = auth_service.generate_state_and_nonce()

    auth_url = auth_service.build_google_auth_url(state, nonce, code_challenge)
    signed_state = auth_service.sign_oauth_state(state, nonce, code_verifier)

    response = RedirectResponse(url=auth_url, status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        key=OAUTH_STATE_COOKIE,
        value=signed_state,
        httponly=True,
        samesite="lax",
        secure=(settings.app_env.lower() == "production"),
        max_age=600,  # 10 minutes
        path="/",
    )
    return response


@router.get("/google/callback", summary="Google OAuth Callback")
async def google_callback(
    request: Request,
    response: Response,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Handles Google OAuth redirect:
    1. Validates state and CSRF cookie.
    2. Exchanges code for ID token via PKCE.
    3. Validates ID token signature, issuer, audience, and nonce.
    4. Synchronizes or creates user in PostgreSQL.
    5. Establishes application session cookie and redirects to dashboard.
    """
    if error:
        logger.warning(f"Google login returned error: {error}")
        return RedirectResponse(url=f"/?auth_error={error}", status_code=status.HTTP_302_FOUND)

    if not code or not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required OAuth parameters (code or state).",
        )

    # Validate state cookie
    state_cookie = request.cookies.get(OAUTH_STATE_COOKIE)
    if not state_cookie:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OAuth state cookie missing or expired. Please initiate login again.",
        )

    stored_data = auth_service.verify_oauth_state(state_cookie)
    if not stored_data or stored_data.get("state") != state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OAuth state parameter. Possible CSRF attempt rejected.",
        )

    nonce = stored_data.get("nonce")
    code_verifier = stored_data.get("code_verifier")

    try:
        # Token Exchange
        token_response = await auth_service.exchange_code_for_tokens(code, code_verifier)
        id_token = token_response.get("id_token")
        if not id_token:
            raise ValueError("No ID token returned by Google.")

        # ID Token Verification
        claims = await auth_service.verify_google_id_token(id_token, expected_nonce=nonce)
        google_sub = claims["sub"]
        email = claims.get("email")
        if not email:
            raise ValueError("Google identity does not include a verified email.")
        full_name = claims.get("name")
        profile_picture = claims.get("picture")

        # Database User Synchronization
        user = auth_service.get_or_create_user(
            db=db,
            google_sub=google_sub,
            email=email,
            full_name=full_name,
            profile_picture=profile_picture,
        )

        # Issue Session Token
        session_token = auth_service.create_session_token(user)

        redirect_response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
        redirect_response.set_cookie(
            key=settings.session_cookie_name,
            value=session_token,
            httponly=True,
            samesite="lax",
            secure=(settings.app_env.lower() == "production"),
            max_age=settings.session_max_age_seconds,
            path="/",
        )
        redirect_response.delete_cookie(OAUTH_STATE_COOKIE, path="/")
        return redirect_response

    except Exception as exc:
        logger.error(f"Google authentication failed: {exc}", exc_info=True)
        return RedirectResponse(url=f"/?auth_error={str(exc)}", status_code=status.HTTP_302_FOUND)


@router.get("/me", response_model=UserOut, summary="Get Current Authenticated User Profile")
async def get_me(current_user: User = Depends(get_current_user)) -> UserOut:
    """Returns safe profile information for the currently authenticated user."""
    return UserOut(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        profile_picture=current_user.profile_picture,
        created_at=current_user.created_at,
        last_login_at=current_user.last_login_at,
    )


@router.get("/status", response_model=AuthStatusResponse, summary="Check Session Authentication Status")
async def get_auth_status(
    current_user: Optional[User] = Depends(get_optional_current_user),
) -> AuthStatusResponse:
    """Non-blocking status check returning whether the current request is authenticated."""
    if not current_user:
        return AuthStatusResponse(authenticated=False, user=None)
    return AuthStatusResponse(
        authenticated=True,
        user=UserOut(
            id=str(current_user.id),
            email=current_user.email,
            full_name=current_user.full_name,
            profile_picture=current_user.profile_picture,
            created_at=current_user.created_at,
            last_login_at=current_user.last_login_at,
        ),
    )


@router.post("/logout", summary="Sign Out and Invalidate Session")
async def logout(response: Response):
    """Clears the authentication session cookie."""
    response.delete_cookie(key=settings.session_cookie_name, path="/")
    return {"message": "Logged out successfully."}


@router.post("/mock-login", summary="Developer Mock Login (Testing & CI)")
async def mock_login(
    payload: MockLoginRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Developer and testing mock sign-in endpoint.
    Enabled when ALLOW_MOCK_AUTH is true or in development/test environments.
    Creates or synchronizes a user and sets the application session cookie.
    """
    if not settings.allow_mock_auth and settings.app_env.lower() == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Mock authentication is disabled in production.",
        )

    clean_email = payload.email.strip().lower()
    google_sub = payload.google_sub or f"mock_google_sub_{hashlib.sha256(clean_email.encode()).hexdigest()[:16]}"
    full_name = payload.full_name or clean_email.split("@")[0].title()
    profile_pic = payload.profile_picture or f"https://ui-avatars.com/api/?name={full_name}&background=6366f1&color=fff"

    user = auth_service.get_or_create_user(
        db=db,
        google_sub=google_sub,
        email=clean_email,
        full_name=full_name,
        profile_picture=profile_pic,
    )

    session_token = auth_service.create_session_token(user)

    response.set_cookie(
        key=settings.session_cookie_name,
        value=session_token,
        httponly=True,
        samesite="lax",
        secure=(settings.app_env.lower() == "production"),
        max_age=settings.session_max_age_seconds,
        path="/",
    )

    return {
        "message": f"Authenticated successfully as {user.email}",
        "access_token": session_token,
        "token_type": "bearer",
        "user": UserOut(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            profile_picture=user.profile_picture,
            created_at=user.created_at,
            last_login_at=user.last_login_at,
        ),
    }
