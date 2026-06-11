import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.deps import get_temp_storage
from app.models.errors import APIError
from app.routers import applications, auth, latex, pipeline, profile, roles, setup
from app.routers import settings as settings_router
from app.utils.logging import get_logger

# Allow OAuth redirect over plain HTTP in local development
if settings.environment == "development":
    os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")

logger = get_logger(__name__)


async def _sweep_loop(interval_seconds: int = 60) -> None:
    """Background task: sweep expired temp files every interval_seconds."""
    while True:
        await asyncio.sleep(interval_seconds)
        try:
            get_temp_storage().sweep_expired()
        except Exception as exc:
            logger.error(f"Temp storage sweep failed: {exc}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_sweep_loop())
    import shutil
    pdflatex = shutil.which("pdflatex")
    pdfinfo = shutil.which("pdfinfo")
    logger.info(
        f"Resume Tailor API starting environment={settings.environment} "
        f"pdflatex={pdflatex or 'NOT FOUND'} pdfinfo={pdfinfo or 'NOT FOUND'}"
    )
    yield
    task.cancel()
    logger.info("Resume Tailor API stopped")


app = FastAPI(title="Resume Tailor API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={"error": exc.to_detail().model_dump()},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(f"Unhandled exception: {type(exc).__name__}: {exc}", exc_info=True)
    tech = str(exc) if settings.environment == "development" else None
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "stage": None,
                "user_message": "An unexpected error occurred. Please try again.",
                "technical_details": tech,
                "retry_possible": True,
                "retry_hint": "If this persists, please contact support.",
                "trace_id": "",
            }
        },
    )


@app.get("/health")
async def health():
    return {"status": "ok", "environment": settings.environment}


app.include_router(latex.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(setup.router, prefix="/api")
app.include_router(profile.router, prefix="/api")
app.include_router(roles.router, prefix="/api")
app.include_router(pipeline.router, prefix="/api")
app.include_router(applications.router, prefix="/api")
app.include_router(settings_router.router, prefix="/api")
