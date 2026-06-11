from pydantic import BaseModel, Field, model_validator

from app.models.critique import Critique
from app.models.outreach import OutreachJson


# ── Tailor agent output models ─────────────────────────────────────────────────

class TailoredExperience(BaseModel):
    role_id: str
    bullets: list[str]


class TailoredProject(BaseModel):
    project_id: str


class TailoredContent(BaseModel):
    summary: str
    skills: dict[str, list[str]]  # insertion order = JD-relevance order
    experience: list[TailoredExperience]
    projects: list[TailoredProject]


# ── Pipeline request / response models ────────────────────────────────────────

class OutreachOptions(BaseModel):
    enabled: bool = True
    contact_name: str | None = None
    contact_type: str | None = None  # "Recruiter" | "Hiring Manager" | "Employee"


class PipelineRequest(BaseModel):
    job_url: str | None = None
    job_description: str | None = None
    company_name: str
    role_title: str
    role_config_id: str
    outreach: OutreachOptions = Field(default_factory=OutreachOptions)

    @model_validator(mode="after")
    def requires_jd_source(self) -> "PipelineRequest":
        if not self.job_url and not self.job_description:
            raise ValueError("Either job_url or job_description must be provided")
        return self


class PipelineRunResponse(BaseModel):
    job_id: str
    status: str = "running"
    stream_url: str
    new: bool = True


class PipelineResultResponse(BaseModel):
    job_id: str
    status: str  # "completed" | "failed" | "running"
    application_id: str | None = None
    drive_folder_id: str | None = None
    current_version: int | None = None
    tailored_latex: str | None = None
    pdf_url: str | None = None
    critique: Critique | None = None
    outreach: OutreachJson | None = None


class RetryRequest(BaseModel):
    from_stage: str


class RetailorRequest(BaseModel):
    application_id: str
    incorporate_feedback: bool = True


class RetailorResponse(BaseModel):
    job_id: str
    status: str = "running"
    stream_url: str
    new: bool = True
    retailor_attempt: int
