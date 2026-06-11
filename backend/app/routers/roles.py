import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.agents.role_config_generator import RoleConfigGeneratorAgent
from app.agents.base import AnyNimClient
from app.deps import get_drive_client, get_nim_client
from app.orchestration.role_resolver import RoleResolver
from app.services.google_drive import GoogleDriveClient
from app.utils.logging import get_logger, set_trace_id

logger = get_logger(__name__)
router = APIRouter()

_ROOT_FOLDER = "Resume_Tailor"


class RoleListResponse(BaseModel):
    roles: list[dict]


class RoleSelectRequest(BaseModel):
    role_id: str


class RoleSelectResponse(BaseModel):
    role_id: str
    display_name: str
    ready: bool = True
    generated_now: bool = False


async def _get_resolver(drive: GoogleDriveClient, nim: AnyNimClient) -> RoleResolver:
    root_id = await drive.find_folder(_ROOT_FOLDER)
    role_configs_id = await drive.find_folder("role_configs", parent_id=root_id) if root_id else None
    generator = RoleConfigGeneratorAgent(nim_client=nim)
    return RoleResolver(
        drive_client=drive,
        generator_agent=generator,
        role_configs_folder_id=role_configs_id or root_id or "",
    )


@router.get("/roles/available", response_model=RoleListResponse)
async def list_roles(
    drive: GoogleDriveClient = Depends(get_drive_client),
) -> RoleListResponse:
    trace_id = set_trace_id()
    logger.info(f"GET /api/roles/available trace_id={trace_id}")
    try:
        root_id = await drive.find_folder(_ROOT_FOLDER)
        role_configs_id = await drive.find_folder("role_configs", parent_id=root_id) if root_id else None
        from app.orchestration.role_resolver import RoleResolver
        resolver = RoleResolver(
            drive_client=drive,
            generator_agent=None,  # type: ignore[arg-type]
            role_configs_folder_id=role_configs_id or root_id or "",
        )
        roles = await resolver.list_available()
    except Exception:
        roles = []
    return RoleListResponse(roles=roles)


@router.post("/roles/select", response_model=RoleSelectResponse)
async def select_role(
    request: RoleSelectRequest,
    drive: GoogleDriveClient = Depends(get_drive_client),
    nim: AnyNimClient = Depends(get_nim_client),
) -> RoleSelectResponse:
    trace_id = set_trace_id()
    logger.info(f"POST /api/roles/select role_id={request.role_id} trace_id={trace_id}")
    resolver = await _get_resolver(drive, nim)

    from app.orchestration.role_resolver import _BUILTIN_DIR
    from app.services.google_drive import GoogleDriveClient as _DriveClient

    builtin_exists = (_BUILTIN_DIR / f"{request.role_id}.json").exists()
    root_id = await drive.find_folder(_ROOT_FOLDER)
    role_configs_id = await drive.find_folder("role_configs", parent_id=root_id) if root_id else None
    drive_exists = False
    if role_configs_id:
        drive_exists = await drive.find_file(f"{request.role_id}.json", parent_id=role_configs_id) is not None
    generated_now = not builtin_exists and not drive_exists

    config = await resolver.resolve(request.role_id)
    return RoleSelectResponse(
        role_id=config.role_id,
        display_name=config.role_display_name,
        ready=True,
        generated_now=generated_now,
    )
