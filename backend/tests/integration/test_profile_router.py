"""Integration tests for /api/profile endpoints.

GoogleDriveClient is mocked at the dependency level — no real Drive calls.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.deps import get_drive_client
from app.main import app
from app.services.google_drive import GoogleDriveClient

_SAMPLE_PROFILE = {
    "version": 1,
    "personal": {
        "name": "Sai Sumanth",
        "email": "sumanth@example.com",
        "phone": "(667) 445-9499",
        "location": "Baltimore, MD",
        "linkedin": None,
        "github": None,
        "portfolio": None,
    },
    "visa_status": {"type": "F-1 OPT", "needs_sponsorship": True, "stem_extension_eligible": True},
    "education": [],
    "experience": [],
    "projects": [],
    "skills": {},
}

_HEADERS = {"Authorization": "Bearer ya29.test"}


def _make_drive_mock(
    root_folder_id: str | None = "root_id",
    profile_data: dict | None = _SAMPLE_PROFILE,
) -> MagicMock:
    drive = MagicMock(spec=GoogleDriveClient)
    drive.find_folder = AsyncMock(return_value=root_folder_id)
    drive.read_json = AsyncMock(return_value=profile_data)
    drive.write_json = AsyncMock(return_value="file_id_123")
    return drive


@pytest.fixture
async def profile_client():
    drive = _make_drive_mock()
    app.dependency_overrides[get_drive_client] = lambda: drive
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c, drive
    app.dependency_overrides.clear()


# ── GET /api/profile ───────────────────────────────────────────────────────────

class TestGetProfile:
    async def test_returns_profile_when_found(self, profile_client):
        c, _ = profile_client
        resp = await c.get("/api/profile", headers=_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["personal"]["name"] == "Sai Sumanth"
        assert data["version"] == 1

    async def test_404_when_root_folder_missing(self):
        drive = _make_drive_mock(root_folder_id=None)
        app.dependency_overrides[get_drive_client] = lambda: drive
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.get("/api/profile", headers=_HEADERS)
            assert resp.status_code == 400
            assert resp.json()["error"]["code"] == "PROFILE_NOT_FOUND"
        finally:
            app.dependency_overrides.clear()

    async def test_404_when_profile_json_missing(self):
        drive = _make_drive_mock(profile_data=None)
        app.dependency_overrides[get_drive_client] = lambda: drive
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.get("/api/profile", headers=_HEADERS)
            assert resp.status_code == 400
            assert resp.json()["error"]["code"] == "PROFILE_NOT_FOUND"
        finally:
            app.dependency_overrides.clear()

    async def test_missing_auth_returns_422(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/profile")
        assert resp.status_code == 422


# ── PUT /api/profile ───────────────────────────────────────────────────────────

class TestPutProfile:
    async def test_saves_profile_successfully(self, profile_client):
        c, drive = profile_client
        resp = await c.put("/api/profile", headers=_HEADERS, json=_SAMPLE_PROFILE)
        assert resp.status_code == 200
        assert resp.json()["saved"] is True
        assert resp.json()["version"] == 1
        drive.write_json.assert_awaited_once()

    async def test_write_json_called_with_correct_filename(self, profile_client):
        c, drive = profile_client
        await c.put("/api/profile", headers=_HEADERS, json=_SAMPLE_PROFILE)
        call_args = drive.write_json.call_args
        assert call_args[0][0] == "profile.json"

    async def test_404_when_root_folder_missing(self):
        drive = _make_drive_mock(root_folder_id=None)
        app.dependency_overrides[get_drive_client] = lambda: drive
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.put("/api/profile", headers=_HEADERS, json=_SAMPLE_PROFILE)
            assert resp.status_code == 400
            assert resp.json()["error"]["code"] == "PROFILE_NOT_FOUND"
        finally:
            app.dependency_overrides.clear()

    async def test_invalid_body_returns_422(self, profile_client):
        c, _ = profile_client
        resp = await c.put("/api/profile", headers=_HEADERS, json={"not_a_profile": True})
        assert resp.status_code == 422


# ── POST /api/profile/parse-from-resume ───────────────────────────────────────

class TestParseFromResume:
    async def test_parses_resume_successfully(self):
        from app.deps import get_nim_client
        from app.services.nvidia_nim_mock import MockNimClient

        drive = _make_drive_mock()
        app.dependency_overrides[get_drive_client] = lambda: drive
        app.dependency_overrides[get_nim_client] = lambda: MockNimClient()
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.post(
                    "/api/profile/parse-from-resume",
                    headers={**_HEADERS, "X-NIM-Key": "nvapi-mock"},
                    files={"file": ("resume.tex", b"\\documentclass{article}\\begin{document}Hello\\end{document}", "text/plain")},
                    data={"format": "tex"},
                )
            assert resp.status_code == 200
            data = resp.json()
            assert "profile" in data
            assert "extraction_confidence" in data
        finally:
            app.dependency_overrides.clear()

    async def test_missing_file_returns_422(self, profile_client):
        c, _ = profile_client
        resp = await c.post(
            "/api/profile/parse-from-resume",
            headers={**_HEADERS, "X-NIM-Key": "nvapi-mock"},
        )
        assert resp.status_code == 422
