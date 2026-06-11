from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import Response

from app.deps import get_latex_compiler, get_temp_storage
from app.models.latex import CompileRequest, CompileResponse
from app.services.google_drive import make_drive_client
from app.services.latex_compiler import LatexCompiler
from app.services.temp_storage import TempStorage
from app.utils.logging import get_logger, set_trace_id

logger = get_logger(__name__)
router = APIRouter()


@router.post("/latex/compile", response_model=CompileResponse)
async def compile_latex(
    request: CompileRequest,
    compiler: LatexCompiler = Depends(get_latex_compiler),
    storage: TempStorage = Depends(get_temp_storage),
) -> CompileResponse:
    trace_id = set_trace_id()
    logger.info(f"Compile request trace_id={trace_id} filename_hint={request.filename_hint}")

    result = await compiler.compile(request.tex_source, request.filename_hint)

    if not result.success:
        return CompileResponse(
            success=False,
            errors=result.errors,
            compile_log=result.compile_log,
        )

    file_id = storage.store(result.pdf_bytes, ext="pdf")
    expires_at = storage.get_expiry_iso(file_id)

    logger.info(f"Compile succeeded trace_id={trace_id} file_id={file_id} pages={result.pages}")
    return CompileResponse(
        success=True,
        pdf_id=file_id,
        pdf_url=f"/api/files/{file_id}",
        pages=result.pages,
        warnings=result.warnings,
        expires_at=expires_at,
    )


@router.get("/files/{file_id}")
async def get_file(
    file_id: str,
    storage: TempStorage = Depends(get_temp_storage),
    authorization: str | None = Header(None),
) -> Response:
    """Serve a PDF by id.

    Two id shapes:
      - `tmp_*`  — an in-flight PDF in temp storage (10-min TTL, no auth needed).
      - anything else — a Google Drive file id for a persisted application PDF,
        fetched on behalf of the user (requires their Bearer token).
    """
    # In-flight temp PDFs.
    if file_id.startswith("tmp_"):
        data = storage.retrieve(file_id)
        if data is None:
            raise HTTPException(status_code=404, detail="File not found or expired")
        return Response(
            content=data,
            media_type="application/pdf",
            headers={"Cache-Control": "private, max-age=600"},
        )

    # Persisted Drive PDFs — proxy the download using the caller's token.
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Authorization header required to fetch Drive files.",
        )
    token = authorization.removeprefix("Bearer ")
    drive = await make_drive_client(access_token=token)
    try:
        data = await drive.download_file(file_id)
    except Exception as exc:
        logger.warning(f"Drive file download failed file_id={file_id}: {exc}")
        raise HTTPException(status_code=404, detail="File not found in Drive.") from exc

    if not data:
        raise HTTPException(status_code=404, detail="File not found in Drive.")

    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Cache-Control": "private, max-age=600"},
    )
