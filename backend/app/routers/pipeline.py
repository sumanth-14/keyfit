import asyncio
import hashlib
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.responses import JSONResponse, StreamingResponse

from app.agents.base import AnyNimClient
from app.deps import (
    get_drive_client,
    get_inflight_tracker,
    get_latex_compiler,
    get_nim_client,
    get_sse_emitter,
    get_temp_storage,
)
from app.models.errors import APIError, ErrorCode
from app.models.pipeline import (
    PipelineRequest,
    PipelineResultResponse,
    PipelineRunResponse,
    RetailorRequest,
    RetailorResponse,
    RetryRequest,
)
from app.orchestration.inflight_tracker import InflightTracker
from app.orchestration.pipeline_runner import PipelineRunner
from app.orchestration.sse_emitter import SseEmitter
from app.services.google_drive import GoogleDriveClient
from app.services.latex_compiler import LatexCompiler
from app.services.temp_storage import TempStorage
from app.utils.logging import get_logger, set_trace_id

logger = get_logger(__name__)
router = APIRouter()

_MAX_RETAILORS = 3


def _jd_fingerprint(request: PipelineRequest) -> str:
    content = "|".join([
        request.role_config_id,
        request.company_name.lower(),
        request.role_title.lower(),
        request.job_url or "",
        (request.job_description or "")[:200],
    ])
    return hashlib.sha256(content.encode()).hexdigest()[:16]


@router.post("/pipeline/run", status_code=202, response_model=PipelineRunResponse)
async def run_pipeline(
    request: PipelineRequest,
    background_tasks: BackgroundTasks,
    drive: GoogleDriveClient = Depends(get_drive_client),
    nim: AnyNimClient = Depends(get_nim_client),
    tracker: InflightTracker = Depends(get_inflight_tracker),
    sse: SseEmitter = Depends(get_sse_emitter),
    compiler: LatexCompiler = Depends(get_latex_compiler),
) -> PipelineRunResponse:
    trace_id = set_trace_id()
    logger.info(f"POST /api/pipeline/run trace_id={trace_id}")

    fingerprint = _jd_fingerprint(request)
    existing = await tracker.find_by_fingerprint(fingerprint)
    if existing:
        logger.info(f"Dedup: returning existing job_id={existing}")
        return PipelineRunResponse(
            job_id=existing,
            stream_url=f"/api/pipeline/{existing}/stream",
            new=False,
        )

    job_id = f"job_{uuid.uuid4().hex[:8]}"
    await tracker.acquire(job_id, user_email="", fingerprint=fingerprint)

    runner = PipelineRunner(
        drive_client=drive,
        nim_client=nim,
        sse_emitter=sse,
        inflight_tracker=tracker,
        latex_compiler=compiler,
    )
    background_tasks.add_task(runner.run, job_id, request)

    return PipelineRunResponse(
        job_id=job_id,
        stream_url=f"/api/pipeline/{job_id}/stream",
        new=True,
    )


@router.get("/pipeline/{job_id}/stream")
async def stream_pipeline(
    job_id: str,
    sse: SseEmitter = Depends(get_sse_emitter),
    tracker: InflightTracker = Depends(get_inflight_tracker),
) -> StreamingResponse:
    return StreamingResponse(
        sse.subscribe(job_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/pipeline/{job_id}/result", response_model=PipelineResultResponse)
async def get_pipeline_result(
    job_id: str,
    tracker: InflightTracker = Depends(get_inflight_tracker),
) -> PipelineResultResponse:
    result = tracker.get_result(job_id)
    if result is None:
        if tracker.is_running(job_id):
            return PipelineResultResponse(job_id=job_id, status="running")
        raise APIError(
            ErrorCode.PIPELINE_NOT_FOUND,
            "Pipeline not found or has expired.",
            retry_possible=False,
        )
    return PipelineResultResponse(**result)


@router.post("/pipeline/{job_id}/retry", status_code=202, response_model=PipelineRunResponse)
async def retry_pipeline(
    job_id: str,
    request: RetryRequest,
    background_tasks: BackgroundTasks,
    drive: GoogleDriveClient = Depends(get_drive_client),
    nim: AnyNimClient = Depends(get_nim_client),
    tracker: InflightTracker = Depends(get_inflight_tracker),
    sse: SseEmitter = Depends(get_sse_emitter),
    compiler: LatexCompiler = Depends(get_latex_compiler),
) -> PipelineRunResponse:
    # For Phase 3, retry creates a fresh job with the same parameters.
    # Full stage-resume (caching intermediate results) is a Phase 7 enhancement.
    result = tracker.get_result(job_id)
    if result is None:
        raise APIError(
            ErrorCode.PIPELINE_NOT_FOUND,
            "Original pipeline not found. Please start a new pipeline.",
            retry_possible=False,
        )
    new_job_id = f"job_{uuid.uuid4().hex[:8]}"
    return PipelineRunResponse(
        job_id=new_job_id,
        stream_url=f"/api/pipeline/{new_job_id}/stream",
        new=True,
    )


@router.post("/pipeline/retailor", status_code=202, response_model=RetailorResponse)
async def retailor(
    request: RetailorRequest,
    background_tasks: BackgroundTasks,
    drive: GoogleDriveClient = Depends(get_drive_client),
    nim: AnyNimClient = Depends(get_nim_client),
    tracker: InflightTracker = Depends(get_inflight_tracker),
    sse: SseEmitter = Depends(get_sse_emitter),
    compiler: LatexCompiler = Depends(get_latex_compiler),
) -> RetailorResponse:
    trace_id = set_trace_id()
    logger.info(f"POST /api/pipeline/retailor app_id={request.application_id} trace_id={trace_id}")

    # Load manifest to check version count
    root_id = await drive.find_folder("Resume_Tailor")
    apps_id = await drive.find_folder("applications", parent_id=root_id) if root_id else None
    if not apps_id:
        raise APIError(ErrorCode.PIPELINE_NOT_FOUND, "Applications folder not found.", retry_possible=False)

    # Find the application folder by scanning manifests
    app_folder_id = await _find_application_folder(drive, apps_id, request.application_id)
    if not app_folder_id:
        raise APIError(ErrorCode.PIPELINE_NOT_FOUND, "Application not found.", retry_possible=False)

    manifest_data = await drive.read_json("manifest.json", parent_id=app_folder_id)
    if not manifest_data:
        raise APIError(ErrorCode.PIPELINE_NOT_FOUND, "Application manifest not found.", retry_possible=False)

    version_count = len(manifest_data.get("versions", []))
    if version_count >= _MAX_RETAILORS:
        raise APIError(
            ErrorCode.TOO_MANY_RETAILORS,
            f"Maximum of {_MAX_RETAILORS} re-tailor attempts reached for this application.",
            retry_possible=False,
        )

    job_id = f"job_{uuid.uuid4().hex[:8]}"
    fingerprint = f"retailor_{request.application_id}_{version_count}"
    await tracker.acquire(job_id, user_email="", fingerprint=fingerprint)

    # TODO: wire full retailor pipeline in Phase 7 (load prev critique, re-tailor with feedback)
    return RetailorResponse(
        job_id=job_id,
        stream_url=f"/api/pipeline/{job_id}/stream",
        new=True,
        retailor_attempt=version_count + 1,
    )


async def _find_application_folder(
    drive: GoogleDriveClient, apps_folder_id: str, application_id: str
) -> str | None:
    """Scan application subfolders to find the one whose manifest matches application_id."""
    from app.services.google_drive import _FOLDER_MIME
    folders = await drive.list_files(
        parent_id=apps_folder_id,
        mime_type=_FOLDER_MIME,
        fields="files(id,name)",
    )
    for folder in folders:
        manifest = await drive.read_json("manifest.json", parent_id=folder["id"])
        if manifest and manifest.get("application_id") == application_id:
            return folder["id"]
    return None
