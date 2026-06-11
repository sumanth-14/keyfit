import asyncio
import base64
import hashlib
import os
import secrets
from datetime import datetime, timezone
from functools import partial

import httpx
from google_auth_oauthlib.flow import Flow

from app.models.auth import OAuthCallbackResponse
from app.models.errors import APIError, ErrorCode
from app.utils.logging import get_logger

logger = get_logger(__name__)

_SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]
_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


class GoogleOAuthService:
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    def _make_flow(self) -> Flow:
        client_config = {
            "web": {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [self.redirect_uri],
            }
        }
        flow = Flow.from_client_config(client_config, scopes=_SCOPES)
        flow.redirect_uri = self.redirect_uri
        return flow

    def get_auth_url(self, state: str) -> tuple[str, str]:
        """Return (auth_url, code_verifier). Frontend must store code_verifier and send it back."""
        if not self.client_id:
            raise APIError(
                ErrorCode.INTERNAL_ERROR,
                "Google OAuth is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.",
            )
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).rstrip(b"=").decode()

        flow = self._make_flow()
        auth_url, _ = flow.authorization_url(
            state=state,
            access_type="offline",
            prompt="consent",
            include_granted_scopes="true",
            code_challenge=code_challenge,
            code_challenge_method="S256",
        )
        return auth_url, code_verifier

    async def exchange_code(self, code: str, code_verifier: str) -> OAuthCallbackResponse:
        """Exchange an authorization code for tokens and fetch the user's email."""
        if not self.client_id:
            raise APIError(
                ErrorCode.INTERNAL_ERROR,
                "Google OAuth is not configured.",
            )

        flow = self._make_flow()

        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(
                None, partial(flow.fetch_token, code=code, code_verifier=code_verifier)
            )
        except Exception as exc:
            logger.warning(f"OAuth token exchange failed: {exc}")
            raise APIError(
                ErrorCode.DRIVE_AUTH_EXPIRED,
                "Could not exchange the authorization code. It may have expired — please try signing in again.",
                technical_details=str(exc),
                retry_possible=True,
            )

        creds = flow.credentials

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    _USERINFO_URL,
                    headers={"Authorization": f"Bearer {creds.token}"},
                    timeout=10,
                )
                resp.raise_for_status()
                user_info = resp.json()
            except Exception as exc:
                logger.warning(f"Userinfo fetch failed: {exc}")
                user_info = {}

        expires_in = 3599
        if creds.expiry:
            remaining = (
                creds.expiry.replace(tzinfo=timezone.utc) - datetime.now(timezone.utc)
            ).seconds
            expires_in = max(remaining, 0)

        return OAuthCallbackResponse(
            access_token=creds.token,
            refresh_token=creds.refresh_token,
            expires_in=expires_in,
            user_email=user_info.get("email", ""),
            tailor_folder_exists=False,  # Set by the auth router after a Drive check
        )
