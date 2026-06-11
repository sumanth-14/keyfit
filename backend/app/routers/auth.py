import secrets

from fastapi import APIRouter, Depends

from app.deps import get_oauth_service
from app.models.auth import AuthUrlResponse, OAuthCallbackRequest, OAuthCallbackResponse
from app.services.google_drive import make_drive_client
from app.services.google_oauth import GoogleOAuthService
from app.utils.logging import get_logger, set_trace_id

logger = get_logger(__name__)
router = APIRouter()

_TAILOR_FOLDER = "Resume_Tailor"


@router.get("/auth/google/url", response_model=AuthUrlResponse)
async def get_auth_url(
    oauth: GoogleOAuthService = Depends(get_oauth_service),
) -> AuthUrlResponse:
    state = secrets.token_hex(16)
    auth_url, code_verifier = oauth.get_auth_url(state=state)
    return AuthUrlResponse(auth_url=auth_url, state=state, code_verifier=code_verifier)


@router.post("/auth/google/callback", response_model=OAuthCallbackResponse)
async def google_callback(
    request: OAuthCallbackRequest,
    oauth: GoogleOAuthService = Depends(get_oauth_service),
) -> OAuthCallbackResponse:
    trace_id = set_trace_id()
    logger.info(f"OAuth callback trace_id={trace_id}")

    token_data = await oauth.exchange_code(request.code, request.code_verifier)

    # Check whether the user already has a Resume_Tailor folder so the frontend
    # can route directly to /dashboard instead of /onboarding.
    drive = await make_drive_client(access_token=token_data.access_token)
    folder_id = await drive.find_folder(_TAILOR_FOLDER)
    token_data.tailor_folder_exists = folder_id is not None

    logger.info(
        f"OAuth callback complete trace_id={trace_id} "
        f"email={token_data.user_email} folder_exists={token_data.tailor_folder_exists}"
    )
    return token_data
