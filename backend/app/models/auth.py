from pydantic import BaseModel


class AuthUrlResponse(BaseModel):
    auth_url: str
    state: str
    code_verifier: str  # PKCE — frontend stores this and sends it back on callback


class OAuthCallbackRequest(BaseModel):
    code: str
    state: str
    code_verifier: str  # PKCE — must match what was used to generate the auth URL


class OAuthCallbackResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    expires_in: int
    user_email: str
    tailor_folder_exists: bool
