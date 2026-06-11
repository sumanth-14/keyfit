import os
from functools import lru_cache

from fastapi import Depends, Header, HTTPException

from app.config import settings
from app.services.google_drive import GoogleDriveClient, make_drive_client
from app.services.google_oauth import GoogleOAuthService
from app.services.latex_compiler import LatexCompiler
from app.services.nvidia_nim import NimClient
from app.services.nvidia_nim_mock import MockNimClient
from app.services.temp_storage import TempStorage


# ── Phase 1: LaTeX / temp storage ─────────────────────────────────────────────

@lru_cache(maxsize=1)
def get_temp_storage() -> TempStorage:
    return TempStorage(
        storage_dir=settings.temp_storage_dir,
        ttl_seconds=settings.temp_storage_ttl_seconds,
    )


@lru_cache(maxsize=1)
def get_latex_compiler() -> LatexCompiler:
    work_dir = os.path.join(settings.temp_storage_dir, "builds")
    return LatexCompiler(work_dir=work_dir)


# ── Phase 2: Google OAuth + Drive ─────────────────────────────────────────────

@lru_cache(maxsize=1)
def get_oauth_service() -> GoogleOAuthService:
    return GoogleOAuthService(
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        redirect_uri=settings.google_redirect_uri,
    )


async def get_drive_token(
    authorization: str = Header(..., description="Bearer {google_access_token}"),
) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header must be 'Bearer <token>'")
    return authorization.removeprefix("Bearer ")


async def get_drive_client(
    token: str = Depends(get_drive_token),
) -> GoogleDriveClient:
    return await make_drive_client(access_token=token)


# ── Phase 3: NIM client ────────────────────────────────────────────────────────

async def get_nim_client(
    x_nim_key: str = Header(..., description="NVIDIA NIM API key"),
) -> NimClient | MockNimClient:
    """Return a NimClient (real or mock) for the current request.

    Key is request-scoped — never persisted (Rule 2).
    """
    if settings.use_mock_nim:
        return MockNimClient()
    return NimClient(api_key=x_nim_key, base_url=settings.nim_base_url)


# ── Phase 3: Orchestration singletons ─────────────────────────────────────────

@lru_cache(maxsize=1)
def get_inflight_tracker():
    from app.orchestration.inflight_tracker import InflightTracker
    return InflightTracker()


@lru_cache(maxsize=1)
def get_sse_emitter():
    from app.orchestration.sse_emitter import SseEmitter
    return SseEmitter()
