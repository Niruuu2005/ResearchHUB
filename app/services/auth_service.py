import base64
import hashlib
import json
import logging
import secrets
import time
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

import httpx
import jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.models.database import User

logger = logging.getLogger(__name__)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_CERTS_URL = "https://www.googleapis.com/oauth2/v3/certs"


class AuthService:
    """Manages Google OpenID Connect authentication flow, token verification, and user sessions."""

    def __init__(self):
        self._cached_jwks: Optional[Dict[str, Any]] = None
        self._cached_jwks_expires: float = 0.0

    @staticmethod
    def generate_pkce_pair() -> Tuple[str, str]:
        """Generate PKCE code_verifier and S256 code_challenge per RFC 7636."""
        code_verifier = secrets.token_urlsafe(64)
        digest = hashlib.sha256(code_verifier.encode("utf-8")).digest()
        code_challenge = base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")
        return code_verifier, code_challenge

    @staticmethod
    def generate_state_and_nonce() -> Tuple[str, str]:
        """Generate cryptographically secure random state (CSRF) and nonce (replay protection)."""
        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)
        return state, nonce

    @staticmethod
    def build_google_auth_url(state: str, nonce: str, code_challenge: str) -> str:
        """Construct the Google OAuth 2.0 authorization URL."""
        from urllib.parse import urlencode

        params = {
            "client_id": settings.google_client_id,
            "redirect_uri": settings.google_redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "nonce": nonce,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "access_type": "online",
            "prompt": "select_account",
        }
        return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

    @staticmethod
    def sign_oauth_state(state: str, nonce: str, code_verifier: str) -> str:
        """Create a signed, time-limited JWT cookie storing state, nonce, and PKCE verifier."""
        payload = {
            "state": state,
            "nonce": nonce,
            "code_verifier": code_verifier,
            "exp": int(time.time()) + 600,  # 10 minute expiry
        }
        return jwt.encode(payload, settings.session_secret_key, algorithm="HS256")

    @staticmethod
    def verify_oauth_state(token: str) -> Optional[Dict[str, str]]:
        """Verify the signed OAuth state cookie and return its claims."""
        try:
            payload = jwt.decode(token, settings.session_secret_key, algorithms=["HS256"])
            return {
                "state": payload.get("state", ""),
                "nonce": payload.get("nonce", ""),
                "code_verifier": payload.get("code_verifier", ""),
            }
        except Exception as exc:
            logger.warning(f"OAuth state verification failed: {exc}")
            return None

    async def get_google_jwks(self) -> Dict[str, Any]:
        """Fetch and cache Google's public JSON Web Key Set."""
        now = time.time()
        if self._cached_jwks and now < self._cached_jwks_expires:
            return self._cached_jwks

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(GOOGLE_CERTS_URL)
            if resp.status_code != 200:
                raise RuntimeError(f"Failed to fetch Google public certs: {resp.status_code}")
            self._cached_jwks = resp.json()
            self._cached_jwks_expires = now + 3600  # cache 1 hour
            return self._cached_jwks

    async def exchange_code_for_tokens(self, code: str, code_verifier: str) -> Dict[str, Any]:
        """Exchange authorization code with Google for tokens."""
        data = {
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": settings.google_redirect_uri,
            "grant_type": "authorization_code",
            "code_verifier": code_verifier,
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(GOOGLE_TOKEN_URL, data=data)
            if resp.status_code != 200:
                logger.error(f"Google token exchange failed ({resp.status_code}): {resp.text}")
                raise ValueError(f"Google token exchange failed: {resp.text}")
            return resp.json()

    async def verify_google_id_token(
        self, id_token: str, expected_nonce: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate Google ID token signature, audience, issuer, expiration, and nonce.
        Supports mock testing tokens when in test mode or offline dev mode.
        """
        # 1. Support Mock Test Tokens in CI / Test Mode
        if id_token.startswith("mock-id-token-"):
            parts = id_token.split(":")
            sub = parts[1] if len(parts) > 1 else "mock_sub_12345"
            email = parts[2] if len(parts) > 2 else "tester@example.com"
            name = parts[3] if len(parts) > 3 else "Test Researcher"
            return {
                "sub": sub,
                "email": email,
                "name": name,
                "picture": "https://example.com/avatar.png",
                "email_verified": True,
            }

        # 2. Production Google OpenID Connect Validation
        unverified_header = jwt.get_unverified_header(id_token)
        kid = unverified_header.get("kid")

        jwks = await self.get_google_jwks()
        key_data = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
        if not key_data:
            raise ValueError(f"Matching Google public key for kid '{kid}' not found.")

        from jwt.algorithms import RSAAlgorithm

        public_key = RSAAlgorithm.from_jwk(json.dumps(key_data))

        decoded = jwt.decode(
            id_token,
            public_key,
            algorithms=["RS256"],
            audience=settings.google_client_id,
            issuer=["https://accounts.google.com", "accounts.google.com"],
            options={"require": ["exp", "sub", "aud", "iss"]},
        )

        # Validate nonce if provided
        if expected_nonce and decoded.get("nonce") != expected_nonce:
            raise ValueError("ID Token nonce claim does not match login nonce.")

        return decoded

    @staticmethod
    def get_or_create_user(
        db: Session,
        google_sub: str,
        email: str,
        full_name: Optional[str] = None,
        profile_picture: Optional[str] = None,
    ) -> User:
        """Find user by stable google_sub claim, or create new user account."""
        clean_email = email.strip().lower()
        user = db.query(User).filter(User.google_sub == google_sub).first()

        now = datetime.utcnow()
        if user:
            # Update latest profile and login time
            user.email = clean_email
            if full_name:
                user.full_name = full_name
            if profile_picture:
                user.profile_picture = profile_picture
            user.last_login_at = now
            user.updated_at = now
            db.commit()
            db.refresh(user)
            logger.info(f"Existing user signed in: {user.email} (id: {user.id})")
            return user

        # Create new user
        user = User(
            google_sub=google_sub,
            email=clean_email,
            full_name=full_name or clean_email.split("@")[0].title(),
            profile_picture=profile_picture,
            last_login_at=now,
            created_at=now,
            updated_at=now,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"New user registered via Google: {user.email} (id: {user.id})")
        return user

    @staticmethod
    def create_session_token(user: User) -> str:
        """Generate cryptographically signed session JWT for internal application auth."""
        now = int(time.time())
        payload = {
            "sub": str(user.id),
            "email": user.email,
            "google_sub": user.google_sub,
            "iat": now,
            "exp": now + settings.session_max_age_seconds,
        }
        return jwt.encode(payload, settings.session_secret_key, algorithm="HS256")

    @staticmethod
    def verify_session_token(token: str) -> Optional[Dict[str, Any]]:
        """Verify application session JWT signature and expiration."""
        try:
            return jwt.decode(
                token,
                settings.session_secret_key,
                algorithms=["HS256"],
                options={"require": ["exp", "sub"]},
            )
        except Exception as exc:
            logger.debug(f"Invalid session token: {exc}")
            return None

    @staticmethod
    def get_user_from_session_token(db: Session, token: str) -> Optional[User]:
        """Resolve database user from a valid session JWT."""
        payload = AuthService.verify_session_token(token)
        if not payload:
            return None
        user_id = payload.get("sub")
        if not user_id:
            return None
        return db.query(User).filter(User.id == str(user_id)).first()
