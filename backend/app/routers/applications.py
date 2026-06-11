from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.deps import get_drive_client
from app.models.application import (
    ApplicationDetail,
    ApplicationListItem,
    ApplicationListResponse,
    ApplicationManifest,
    VersionData,
)
from app.models.critique import Critique
from app.models.errors import APIError, ErrorCode
from app.models.outreach import OutreachJson, OutreachMessages
from app.services.google_drive import GoogleDriveClient, _FOLDER_MIME
from app.utils.logging import get_logger, set_trace_id

logger = get_logger(__name__)
router = APIRouter()

_ROOT_FOLDER = "Resume_Tailor"


async def _get_app_folders(drive: GoogleDriveClient) -> tuple[str | None, list[dict]]:
    """Return (apps_folder_id, list of subfolder metadata)."""
    root_id = await drive.find_folder(_ROOT_FOLDER)
    if not root_id:
        return None, []
    apps_id = await drive.find_folder("applications", parent_id=root_id)
    if not apps_id:
        return apps_id, []
    folders = await drive.list_files(
        parent_id=apps_id,
        mime_type=_FOLDER_MIME,
        fields="files(id,name,createdTime)",
    )
    return apps_id, folders


@router.get("/applications", response_model=ApplicationListResponse)
async def list_applications(
    limit: int = 50,
    offset: int = 0,
    drive: GoogleDriveClient = Depends(get_drive_client),
) -> ApplicationListResponse:
    trace_id = set_trace_id()
    logger.info(f"GET /api/applications trace_id={trace_id}")

    _, folders = await _get_app_folders(drive)

    items: list[ApplicationListItem] = []
    for folder in folders:
        manifest_data = await drive.read_json("manifest.json", parent_id=folder["id"])
        if not manifest_data:
            continue
        manifest = ApplicationManifest.model_validate(manifest_data)
        current = next(
            (v for v in manifest.versions if v.version == manifest.current_version),
            manifest.versions[-1] if manifest.versions else None,
        )
        items.append(
            ApplicationListItem(
                application_id=manifest.application_id,
                folder_name=folder["name"],
                company=manifest.company,
                role_title=manifest.role_title,
                created_at=manifest.created_at,
                current_version=manifest.current_version,
                score=current.score if current else 0,
                verdict=current.verdict if current else "UNKNOWN",
                color=current.color if current else "red",
                status=manifest.status,
            )
        )

    # Sort newest first
    items.sort(key=lambda x: x.created_at, reverse=True)
    total = len(items)
    page = items[offset : offset + limit]

    return ApplicationListResponse(applications=page, total=total, offset=offset, limit=limit)


@router.get("/applications/{application_id}", response_model=ApplicationDetail)
async def get_application(
    application_id: str,
    drive: GoogleDriveClient = Depends(get_drive_client),
) -> ApplicationDetail:
    trace_id = set_trace_id()
    logger.info(f"GET /api/applications/{application_id} trace_id={trace_id}")

    _, folders = await _get_app_folders(drive)
    folder_id = await _find_app_folder(drive, folders, application_id)
    if not folder_id:
        raise APIError(
            ErrorCode.PIPELINE_NOT_FOUND,
            "Application not found.",
            retry_possible=False,
        )

    manifest_data = await drive.read_json("manifest.json", parent_id=folder_id)
    manifest = ApplicationManifest.model_validate(manifest_data)

    version_data = await _load_version_data(drive, folder_id, manifest, manifest.current_version)
    outreach = await _load_outreach(drive, folder_id, manifest)

    return ApplicationDetail(manifest=manifest, current_version_data=version_data, outreach=outreach)


@router.get("/applications/{application_id}/version/{version_num}", response_model=VersionData)
async def get_application_version(
    application_id: str,
    version_num: int,
    drive: GoogleDriveClient = Depends(get_drive_client),
) -> VersionData:
    _, folders = await _get_app_folders(drive)
    folder_id = await _find_app_folder(drive, folders, application_id)
    if not folder_id:
        raise APIError(ErrorCode.PIPELINE_NOT_FOUND, "Application not found.", retry_possible=False)

    manifest_data = await drive.read_json("manifest.json", parent_id=folder_id)
    manifest = ApplicationManifest.model_validate(manifest_data)
    return await _load_version_data(drive, folder_id, manifest, version_num)


class SetCurrentRequest(BaseModel):
    version: int


class SetCurrentResponse(BaseModel):
    current_version: int


@router.post("/applications/{application_id}/set-current", response_model=SetCurrentResponse)
async def set_current_version(
    application_id: str,
    request: SetCurrentRequest,
    drive: GoogleDriveClient = Depends(get_drive_client),
) -> SetCurrentResponse:
    _, folders = await _get_app_folders(drive)
    folder_id = await _find_app_folder(drive, folders, application_id)
    if not folder_id:
        raise APIError(ErrorCode.PIPELINE_NOT_FOUND, "Application not found.", retry_possible=False)

    manifest_data = await drive.read_json("manifest.json", parent_id=folder_id)
    manifest = ApplicationManifest.model_validate(manifest_data)

    valid_versions = {v.version for v in manifest.versions}
    if request.version not in valid_versions:
        raise APIError(ErrorCode.INTERNAL_ERROR, f"Version {request.version} does not exist.", retry_possible=False)

    manifest.current_version = request.version
    await drive.write_json("manifest.json", manifest.model_dump(), parent_id=folder_id)
    return SetCurrentResponse(current_version=request.version)


class DeleteResponse(BaseModel):
    deleted: bool


@router.delete("/applications/{application_id}", response_model=DeleteResponse)
async def delete_application(
    application_id: str,
    drive: GoogleDriveClient = Depends(get_drive_client),
) -> DeleteResponse:
    _, folders = await _get_app_folders(drive)
    folder_id = await _find_app_folder(drive, folders, application_id)
    if not folder_id:
        raise APIError(ErrorCode.PIPELINE_NOT_FOUND, "Application not found.", retry_possible=False)

    deleted = await drive.delete_file(folder_id)
    return DeleteResponse(deleted=deleted)


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _find_app_folder(
    drive: GoogleDriveClient, folders: list[dict], application_id: str
) -> str | None:
    for folder in folders:
        manifest = await drive.read_json("manifest.json", parent_id=folder["id"])
        if manifest and manifest.get("application_id") == application_id:
            return folder["id"]
    return None


async def _load_version_data(
    drive: GoogleDriveClient,
    folder_id: str,
    manifest: ApplicationManifest,
    version_num: int,
) -> VersionData:
    version = next((v for v in manifest.versions if v.version == version_num), None)
    if not version:
        raise APIError(
            ErrorCode.PIPELINE_NOT_FOUND,
            f"Version {version_num} not found.",
            retry_possible=False,
        )

    tex_bytes = None
    tex_file_id = await drive.find_file(version.files.tex, parent_id=folder_id)
    if tex_file_id:
        tex_bytes = await drive.download_file(tex_file_id)
    tex_source = tex_bytes.decode("utf-8") if tex_bytes else ""

    pdf_file_id = await drive.find_file(version.files.pdf, parent_id=folder_id)
    pdf_url = f"/api/files/{pdf_file_id}" if pdf_file_id else ""

    critique_data = await drive.read_json(version.files.critique, parent_id=folder_id)
    critique = Critique.model_validate(critique_data) if critique_data else None

    return VersionData(tex_source=tex_source, pdf_url=pdf_url, critique=critique)


async def _load_outreach(
    drive: GoogleDriveClient,
    folder_id: str,
    manifest: ApplicationManifest,
) -> OutreachMessages | None:
    if not manifest.outreach_file:
        return None
    data = await drive.read_json(manifest.outreach_file, parent_id=folder_id)
    if not data:
        return None
    outreach = OutreachJson.model_validate(data)
    return outreach.messages
