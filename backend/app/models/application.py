from pydantic import BaseModel, Field

from app.models.critique import Critique
from app.models.outreach import OutreachMessages


class ApplicationVersionFiles(BaseModel):
    tex: str
    pdf: str
    critique: str


class ApplicationVersion(BaseModel):
    version: int
    score: int
    verdict: str
    color: str
    files: ApplicationVersionFiles


class PipelineMetadata(BaseModel):
    model_used: str = ""
    total_duration_seconds: float = 0.0


class ApplicationManifest(BaseModel):
    version: int = 1
    application_id: str
    created_at: str
    last_modified: str
    company: str
    role_title: str
    role_config_used: str
    job_url: str | None = None
    current_version: int = 1
    versions: list[ApplicationVersion] = Field(default_factory=list)
    outreach_file: str | None = None
    status: str = "tailored"  # "tailored" | "editing" | "archived"
    pipeline_metadata: PipelineMetadata = Field(default_factory=PipelineMetadata)


class ApplicationListItem(BaseModel):
    application_id: str
    folder_name: str
    company: str
    role_title: str
    created_at: str
    current_version: int
    score: int
    verdict: str
    color: str
    status: str


class ApplicationListResponse(BaseModel):
    applications: list[ApplicationListItem]
    total: int
    offset: int
    limit: int


class VersionData(BaseModel):
    tex_source: str
    pdf_url: str
    critique: Critique | None = None


class ApplicationDetail(BaseModel):
    manifest: ApplicationManifest
    current_version_data: VersionData
    outreach: OutreachMessages | None = None
