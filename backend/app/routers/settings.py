from fastapi import APIRouter, Depends

from app.deps import get_drive_client
from app.models.settings import (
    EncryptedKeyBlob,
    NimKeyGetResponse,
    NimKeyPutResponse,
)
from app.services.google_drive import GoogleDriveClient
from app.utils.logging import get_logger, set_trace_id

logger = get_logger(__name__)
router = APIRouter()

_ROOT_FOLDER = "Resume_Tailor"
_KEY_FILE = "nim_key.json"


@router.get("/settings/nim-key", response_model=NimKeyGetResponse)
async def get_nim_key(
    drive: GoogleDriveClient = Depends(get_drive_client),
) -> NimKeyGetResponse:
    """Return the user's stored encrypted NIM key blob, if any.

    The blob is opaque to us — only the client can decrypt it (Rule 2).
    """
    set_trace_id()
    root_id = await drive.find_folder(_ROOT_FOLDER)
    if not root_id:
        return NimKeyGetResponse(exists=False)
    data = await drive.read_json(_KEY_FILE, parent_id=root_id)
    if not data:
        return NimKeyGetResponse(exists=False)
    return NimKeyGetResponse(exists=True, blob=EncryptedKeyBlob.model_validate(data))


@router.put("/settings/nim-key", response_model=NimKeyPutResponse)
async def put_nim_key(
    blob: EncryptedKeyBlob,
    drive: GoogleDriveClient = Depends(get_drive_client),
) -> NimKeyPutResponse:
    """Persist the user's encrypted NIM key blob to their Drive."""
    trace_id = set_trace_id()
    root_id = await drive.find_folder(_ROOT_FOLDER)
    if not root_id:
        root_id, _ = await drive.ensure_folder(_ROOT_FOLDER)
    await drive.write_json(_KEY_FILE, blob.model_dump(), parent_id=root_id)
    logger.info(f"Stored encrypted NIM key blob trace_id={trace_id}")
    return NimKeyPutResponse(saved=True)
