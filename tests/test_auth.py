import json
import time
import uuid
import pytest
from starlette.testclient import TestClient

from app.config import settings
from app.db.session import SessionLocal
from app.main import app
from app.models.database import User
from app.services.auth_service import AuthService

client = TestClient(app)


def test_unauthenticated_request_is_rejected():
    """Verify that requests without credentials to protected endpoints return HTTP 401."""
    res = client.get("/api/papers", headers={"X-Test-Anonymous": "true"})
    assert res.status_code == 401
    assert "Authentication required" in res.json()["detail"]


def test_invalid_session_token_is_rejected():
    """Verify that an invalid/tampered session JWT returns HTTP 401."""
    res = client.get(
        "/api/papers",
        headers={"Authorization": "Bearer invalid.tampered.token"},
    )
    assert res.status_code == 401
    assert "Invalid or expired session" in res.json()["detail"]


def test_expired_session_token_is_rejected():
    """Verify that an expired session JWT returns HTTP 401."""
    # Create an expired token
    import jwt
    expired_payload = {
        "sub": str(uuid.uuid4()),
        "email": "expired@example.com",
        "google_sub": "expired_sub_123",
        "iat": int(time.time()) - 7200,
        "exp": int(time.time()) - 3600,
    }
    expired_token = jwt.encode(expired_payload, settings.session_secret_key, algorithm="HS256")
    res = client.get(
        "/api/papers",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert res.status_code == 401


def test_google_login_starts_oidc_flow():
    """Verify that /auth/google/login initiates Google OIDC authorization code flow."""
    object.__setattr__(settings, "google_client_id", "test-google-client-id.apps.googleusercontent.com")
    try:
        res = client.get("/auth/google/login", follow_redirects=False, headers={"X-Test-Anonymous": "true"})
        assert res.status_code in (302, 307)
        location = res.headers["location"]
        assert "accounts.google.com/o/oauth2/v2/auth" in location
        assert "response_type=code" in location
        assert "client_id=" in location
        assert "code_challenge=" in location
        assert "code_challenge_method=S256"
        assert "scope=" in location

        # Verify signed OAuth state cookie is set
        cookies = res.cookies
        assert "rh_oauth_state" in cookies
    finally:
        object.__setattr__(settings, "google_client_id", "")


def test_callback_rejects_missing_state():
    """Verify that callback rejects missing or invalid OAuth state parameter (CSRF protection)."""
    res = client.get(
        "/auth/google/callback?code=mock_code&state=invalid_or_missing",
        headers={"X-Test-Anonymous": "true"},
    )
    assert res.status_code == 400
    assert "state" in res.json()["detail"].lower()


def test_mock_login_creates_new_user():
    """Verify that first-time login creates a user in PostgreSQL and sets HttpOnly session cookie."""
    unique_sub = f"google_sub_{uuid.uuid4()}"
    unique_email = f"researcher_{uuid.uuid4().hex[:8]}@university.edu"

    res = client.post(
        "/auth/mock-login",
        json={
            "google_sub": unique_sub,
            "email": unique_email,
            "full_name": "Dr. Marie Curie",
            "profile_picture": "https://example.com/marie.jpg",
        },
        headers={"X-Test-Anonymous": "true"},
    )
    assert res.status_code == 200
    data = res.json()
    user_data = data["user"]
    assert user_data["email"] == unique_email
    assert user_data["full_name"] == "Dr. Marie Curie"
    assert "id" in user_data
    user_id = user_data["id"]

    # Verify session cookie is set and secure
    session_cookie = res.cookies.get(settings.session_cookie_name)
    assert session_cookie is not None

    # Verify user exists in database
    with SessionLocal() as db:
        db_user = db.query(User).filter(User.id == user_id).first()
        assert db_user is not None
        assert db_user.google_sub == unique_sub
        assert db_user.email == unique_email


def test_repeated_login_reuses_existing_account():
    """Verify that repeated logins with same google_sub reuse existing user ID without duplicates."""
    stable_sub = f"stable_sub_{uuid.uuid4()}"
    email_v1 = f"user_{uuid.uuid4().hex[:6]}@lab.org"

    # First login
    res1 = client.post(
        "/auth/mock-login",
        json={"google_sub": stable_sub, "email": email_v1, "full_name": "Initial Name"},
        headers={"X-Test-Anonymous": "true"},
    )
    assert res1.status_code == 200
    user_id_1 = res1.json()["user"]["id"]

    # Second login with updated name/picture
    res2 = client.post(
        "/auth/mock-login",
        json={"google_sub": stable_sub, "email": email_v1, "full_name": "Updated Name"},
        headers={"X-Test-Anonymous": "true"},
    )
    assert res2.status_code == 200
    user_id_2 = res2.json()["user"]["id"]

    # Must be exact same database user ID
    assert user_id_1 == user_id_2
    assert res2.json()["user"]["full_name"] == "Updated Name"

    # Verify in DB only 1 record exists with this google_sub
    with SessionLocal() as db:
        users = db.query(User).filter(User.google_sub == stable_sub).all()
        assert len(users) == 1


def test_auth_me_returns_profile():
    """Verify /auth/me returns safe profile info of authenticated user."""
    # Create test user
    with SessionLocal() as db:
        u = User(
            id=str(uuid.uuid4()),
            google_sub=f"me_sub_{uuid.uuid4()}",
            email="me_tester@example.com",
            full_name="Me Tester",
        )
        db.add(u)
        db.commit()
        db.refresh(u)
        token = AuthService.create_session_token(u)

    res = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == str(u.id)
    assert data["email"] == "me_tester@example.com"
    assert data["full_name"] == "Me Tester"
    # Ensure google_sub is not leaked
    assert "google_sub" not in data


def test_logout_clears_cookie():
    """Verify /auth/logout clears session cookie."""
    res = client.post("/auth/logout")
    assert res.status_code == 200
    # Check Set-Cookie clears or expires
    set_cookie = res.headers.get("set-cookie", "")
    assert settings.session_cookie_name in set_cookie
