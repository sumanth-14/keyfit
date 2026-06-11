from fastapi import APIRouter, Depends

from app.deps import get_drive_client
from app.models.setup import SetupResponse
from app.services.google_drive import GoogleDriveClient
from app.utils.logging import get_logger, set_trace_id

logger = get_logger(__name__)
router = APIRouter()

_ROOT_FOLDER = "Resume_Tailor"
_SUBFOLDERS = ["_config", "role_configs", "applications"]


@router.post("/setup/initialize", response_model=SetupResponse)
async def initialize(
    drive: GoogleDriveClient = Depends(get_drive_client),
) -> SetupResponse:
    trace_id = set_trace_id()
    logger.info(f"Setup initialize trace_id={trace_id}")

    root_id, _ = await drive.ensure_folder(_ROOT_FOLDER)

    created: list[str] = []
    for name in _SUBFOLDERS:
        _, was_created = await drive.ensure_folder(name, parent_id=root_id)
        if was_created:
            created.append(name)

    logger.info(f"Setup complete trace_id={trace_id} root_id={root_id} created={created}")
    return SetupResponse(folder_id=root_id, subfolders_created=created, ready=True)
