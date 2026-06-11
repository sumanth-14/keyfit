"""Integration tests for /api/setup/initialize endpoint.

GoogleDriveClient is mocked at the dependency level — no real Drive calls.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.deps import get_drive_client
from app.main import app
from app.services.google_drive import GoogleDriveClient


# ── Fixtures ───────────────────────────────────────────────────────────────────

def _make_drive_mock(
    root_exists: bool = False,
    subfolders_exist: bool = False,
) -> MagicMock:
    """Build a mock GoogleDriveClient for setup tests."""
    drive = MagicMock(spec=GoogleDriveClient)

    root_id = "root_folder_id"
    sub_ids = {
        "_config": "config_id",
        "role_configs": "roles_id",
        "applications": "apps_id",
    }

    async def ensure_folder(name, parent_id=None):
        if name == "Resume_Tailor":
            return root_id, not root_exists
        return sub_ids.get(name, f"{name}_id"), not subfolders_exist

    drive.ensure_folder = ensure_folder
    return drive


@pytest.fixture
async def fresh_client():
    """Client where Drive has no existing folders."""
    mock_drive = _make_drive_mock(root_exists=False, subfolders_exist=False)
    app.dependency_overrides[get_drive_client] = lambda: mock_drive
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
async def existing_client():
    """Client where Resume_Tailor and all subfolders already exist."""
    mock_drive = _make_drive_mock(root_exists=True, subfolders_exist=True)
    app.dependency_overrides[get_drive_client] = lambda: mock_drive
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
    app.dependency_overrides.clear()


# ── POST /api/setup/initialize ────────────────────────────────────────────────

class TestSetupInitialize:
    async def test_creates_all_subfolders_on_fresh_setup(self, fresh_client):
        resp = await fresh_client.post(
            "/api/setup/initialize",
            headers={"Authorization": "Bearer ya29.test"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ready"] is True
        assert data["folder_id"] == "root_folder_id"
        assert set(data["subfolders_created"]) == {"_config", "role_configs", "applications"}

    async def test_idempotent_when_all_folders_exist(self, existing_client):
        resp = await existing_client.post(
            "/api/setup/initialize",
            headers={"Authorization": "Bearer ya29.test"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ready"] is True
        assert data["subfolders_created"] == []

    async def test_missing_auth_header_returns_422(self):
        # No dep override — let the real header validation run.
        # Missing Authorization header → FastAPI returns 422 before Drive is touched.
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            resp = await c.post("/api/setup/initialize")
        assert resp.status_code == 422

    async def test_malformed_auth_header_returns_401(self):
        # No dep override — let get_drive_token validate "Token ..." vs "Bearer ...".
        # HTTPException(401) is raised before make_drive_client is ever called.
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            resp = await c.post(
                "/api/setup/initialize",
                headers={"Authorization": "Token not-a-bearer"},
            )
        assert resp.status_code == 401

    async def test_partially_existing_subfolders(self):
        """Root exists, but only some subfolders exist."""
        created_calls: list[str] = []

        async def ensure_folder(name, parent_id=None):
            if name == "Resume_Tailor":
                return "root_id", False  # Already exists
            if name == "_config":
                return "config_id", False  # Already exists
            created_calls.append(name)
            return f"{name}_id", True  # New

        drive = MagicMock(spec=GoogleDriveClient)
        drive.ensure_folder = ensure_folder

        app.dependency_overrides[get_drive_client] = lambda: drive
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as c:
                resp = await c.post(
                    "/api/setup/initialize",
                    headers={"Authorization": "Bearer ya29.test"},
                )
            assert resp.status_code == 200
            data = resp.json()
            assert set(data["subfolders_created"]) == {"role_configs", "applications"}
        finally:
            app.dependency_overrides.clear()
