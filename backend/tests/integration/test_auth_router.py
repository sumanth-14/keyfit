"""Integration tests for /api/auth/* endpoints.

GoogleOAuthService and GoogleDriveClient are mocked at the dependency level so
no real network calls are made.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.deps import get_oauth_service
from app.main import app
from app.models.auth import OAuthCallbackResponse
from app.services.google_oauth import GoogleOAuthService


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_oauth() -> MagicMock:
    svc = MagicMock(spec=GoogleOAuthService)
    svc.get_auth_url.return_value = (
        "https://accounts.google.com/o/oauth2/auth?client_id=test&state=abc123",
        "test_code_verifier",
    )
    svc.exchange_code = AsyncMock(
        return_value=OAuthCallbackResponse(
            access_token="ya29.test_token",
            refresh_token="1//test_refresh",
            expires_in=3599,
            user_email="sumanth@example.com",
            tailor_folder_exists=False,
        )
    )
    return svc


@pytest.fixture
async def client(mock_oauth):
    app.dependency_overrides[get_oauth_service] = lambda: mock_oauth
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
    app.dependency_overrides.clear()


# ── GET /api/auth/google/url ───────────────────────────────────────────────────

class TestGetAuthUrl:
    async def test_returns_auth_url_and_state(self, client):
        resp = await client.get("/api/auth/google/url")
        assert resp.status_code == 200
        data = resp.json()
        assert "auth_url" in data
        assert "state" in data
        assert "accounts.google.com" in data["auth_url"]

    async def test_state_is_nonempty_hex(self, client):
        resp = await client.get("/api/auth/google/url")
        state = resp.json()["state"]
        assert len(state) > 0
        # Should be hex characters only
        assert all(c in "0123456789abcdef" for c in state)

    async def test_each_call_returns_unique_state(self, client):
        r1 = await client.get("/api/auth/google/url")
        r2 = await client.get("/api/auth/google/url")
        assert r1.json()["state"] != r2.json()["state"]


# ── POST /api/auth/google/callback ────────────────────────────────────────────

class TestGoogleCallback:
    async def test_successful_callback_no_existing_folder(self, client):
        with patch(
            "app.routers.auth.make_drive_client",
            new_callable=AsyncMock,
        ) as mock_make:
            mock_drive = AsyncMock()
            mock_drive.find_folder = AsyncMock(return_value=None)
            mock_make.return_value = mock_drive

            resp = await client.post(
                "/api/auth/google/callback",
                json={"code": "4/0test_code", "state": "abc123", "code_verifier": "v"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["access_token"] == "ya29.test_token"
        assert data["user_email"] == "sumanth@example.com"
        assert data["tailor_folder_exists"] is False

    async def test_callback_with_existing_folder(self, client):
        with patch(
            "app.routers.auth.make_drive_client",
            new_callable=AsyncMock,
        ) as mock_make:
            mock_drive = AsyncMock()
            mock_drive.find_folder = AsyncMock(return_value="folder_id_123")
            mock_make.return_value = mock_drive

            resp = await client.post(
                "/api/auth/google/callback",
                json={"code": "4/0test_code", "state": "abc123", "code_verifier": "v"},
            )

        assert resp.status_code == 200
        assert resp.json()["tailor_folder_exists"] is True

    async def test_callback_missing_fields_returns_422(self, client):
        resp = await client.post("/api/auth/google/callback", json={"code": "only_code"})
        assert resp.status_code == 422

    async def test_callback_exchange_failure_returns_400(self, client, mock_oauth):
        from app.models.errors import APIError, ErrorCode
        mock_oauth.exchange_code = AsyncMock(
            side_effect=APIError(
                ErrorCode.DRIVE_AUTH_EXPIRED,
                "Code expired",
                retry_possible=True,
            )
        )
        with patch("app.routers.auth.make_drive_client", new_callable=AsyncMock):
            resp = await client.post(
                "/api/auth/google/callback",
                json={"code": "bad_code", "state": "abc", "code_verifier": "v"},
            )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "DRIVE_AUTH_EXPIRED"
