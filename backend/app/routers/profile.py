from fastapi import APIRouter, Depends, Form, UploadFile

from app.agents.resume_parser import ResumeParserAgent
from app.deps import get_drive_client, get_nim_client
from app.models.errors import APIError, ErrorCode
from app.models.profile import (
    ExtractionConfidence,
    FlaggedField,
    ParseFromResumeResponse,
    Profile,
    ProfileSaveResponse,
)
from app.services.google_drive import GoogleDriveClient
from app.utils.logging import get_logger, set_trace_id

from app.agents.base import AnyNimClient

logger = get_logger(__name__)
router = APIRouter()

_ROOT_FOLDER = "Resume_Tailor"
_PROFILE_FILE = "profile.json"


async def _get_root_folder_id(drive: GoogleDriveClient) -> str | None:
    """Find the Resume_Tailor root folder ID, or None if it doesn't exist."""
    return await drive.find_folder(_ROOT_FOLDER)


@router.get("/profile", response_model=Profile)
async def get_profile(
    drive: GoogleDriveClient = Depends(get_drive_client),
) -> Profile:
    trace_id = set_trace_id()
    logger.info(f"GET /api/profile trace_id={trace_id}")

    root_id = await _get_root_folder_id(drive)
    if not root_id:
        raise APIError(
            ErrorCode.PROFILE_NOT_FOUND,
            "Drive folder not found. Please complete setup first.",
        )

    data = await drive.read_json(_PROFILE_FILE, parent_id=root_id)
    if data is None:
        raise APIError(
            ErrorCode.PROFILE_NOT_FOUND,
            "Profile not found. Please complete onboarding to create your profile.",
        )

    logger.info(f"Profile loaded trace_id={trace_id}")
    return Profile.model_validate(data)


@router.put("/profile", response_model=ProfileSaveResponse)
async def put_profile(
    profile: Profile,
    drive: GoogleDriveClient = Depends(get_drive_client),
) -> ProfileSaveResponse:
    trace_id = set_trace_id()
    logger.info(f"PUT /api/profile trace_id={trace_id}")

    root_id = await _get_root_folder_id(drive)
    if not root_id:
        raise APIError(
            ErrorCode.PROFILE_NOT_FOUND,
            "Drive folder not found. Please complete setup first.",
        )

    await drive.write_json(_PROFILE_FILE, profile.model_dump(), parent_id=root_id)
    logger.info(f"Profile saved trace_id={trace_id}")
    return ProfileSaveResponse(saved=True, version=profile.version)


@router.post("/profile/parse-from-resume", response_model=ParseFromResumeResponse)
async def parse_from_resume(
    file: UploadFile,
    format: str = Form(default="tex"),
    drive: GoogleDriveClient = Depends(get_drive_client),
    nim: AnyNimClient = Depends(get_nim_client),
) -> ParseFromResumeResponse:
    trace_id = set_trace_id()
    logger.info(f"POST /api/profile/parse-from-resume format={format} trace_id={trace_id}")

    content = await file.read()
    try:
        resume_text = content.decode("utf-8", errors="replace")
    except Exception as exc:
        raise APIError(
            ErrorCode.INTERNAL_ERROR,
            "Could not read the uploaded file.",
            technical_details=str(exc),
            retry_possible=False,
        ) from exc

    agent = ResumeParserAgent(nim_client=nim)
    result = await agent.run(resume_text=resume_text)

    confidence_data = result.pop("extraction_confidence", {})
    flagged_raw = result.pop("flagged_fields", [])
    raw_text = result.pop("raw_extracted_text", resume_text[:500])

    profile = Profile.model_validate(result)
    confidence = ExtractionConfidence.model_validate(confidence_data)
    flagged = [FlaggedField.model_validate(f) for f in flagged_raw]

    logger.info(f"Resume parsed trace_id={trace_id}")
    return ParseFromResumeResponse(
        profile=profile,
        extraction_confidence=confidence,
        flagged_fields=flagged,
        raw_extracted_text=raw_text,
    )
