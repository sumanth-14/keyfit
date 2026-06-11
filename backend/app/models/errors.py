from enum import Enum

from pydantic import BaseModel


class ErrorCode(str, Enum):
    SCRAPE_FAILED = "SCRAPE_FAILED"
    SCRAPE_BLOCKED = "SCRAPE_BLOCKED"
    JD_ANALYZER_FAILED = "JD_ANALYZER_FAILED"
    TAILOR_FAILED = "TAILOR_FAILED"
    TAILOR_NO_BULLETS = "TAILOR_NO_BULLETS"
    TAILOR_VALIDATION_FAILED = "TAILOR_VALIDATION_FAILED"
    LATEX_COMPILE_FAILED = "LATEX_COMPILE_FAILED"
    PAGE_FIT_FAILED = "PAGE_FIT_FAILED"
    CRITIC_FAILED = "CRITIC_FAILED"
    OUTREACH_FAILED = "OUTREACH_FAILED"
    DRIVE_AUTH_EXPIRED = "DRIVE_AUTH_EXPIRED"
    DRIVE_QUOTA_EXCEEDED = "DRIVE_QUOTA_EXCEEDED"
    NIM_KEY_INVALID = "NIM_KEY_INVALID"
    NIM_RATE_LIMITED = "NIM_RATE_LIMITED"
    NIM_MODEL_UNAVAILABLE = "NIM_MODEL_UNAVAILABLE"
    PROFILE_NOT_FOUND = "PROFILE_NOT_FOUND"
    PROFILE_INCOMPLETE = "PROFILE_INCOMPLETE"
    TOO_MANY_RETAILORS = "TOO_MANY_RETAILORS"
    PIPELINE_NOT_FOUND = "PIPELINE_NOT_FOUND"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ErrorDetail(BaseModel):
    code: ErrorCode
    stage: str | None = None
    user_message: str
    technical_details: str | None = None
    retry_possible: bool = False
    retry_hint: str | None = None
    trace_id: str = ""


class APIError(Exception):
    """Raised when the backend wants to return a structured error response."""

    def __init__(
        self,
        code: ErrorCode,
        user_message: str,
        *,
        stage: str | None = None,
        technical_details: str | None = None,
        retry_possible: bool = False,
        retry_hint: str | None = None,
        trace_id: str = "",
    ) -> None:
        super().__init__(user_message)
        self.code = code
        self.stage = stage
        self.user_message = user_message
        self.technical_details = technical_details
        self.retry_possible = retry_possible
        self.retry_hint = retry_hint
        self.trace_id = trace_id

    def to_detail(self) -> ErrorDetail:
        return ErrorDetail(
            code=self.code,
            stage=self.stage,
            user_message=self.user_message,
            technical_details=self.technical_details,
            retry_possible=self.retry_possible,
            retry_hint=self.retry_hint,
            trace_id=self.trace_id,
        )


class StageError(APIError):
    """Raised inside pipeline stages — carries stage name automatically."""

    def __init__(
        self, stage: str, code: ErrorCode, user_message: str, **kwargs
    ) -> None:
        super().__init__(code, user_message, stage=stage, **kwargs)
