from pydantic import BaseModel, Field


class PersonalInfo(BaseModel):
    name: str
    email: str
    phone: str | None = None
    location: str | None = None
    linkedin: str | None = None
    github: str | None = None
    github_display: str | None = None  # human-readable label, e.g. "github.com/sumanth-14"
    portfolio: str | None = None


class VisaStatus(BaseModel):
    type: str
    needs_sponsorship: bool = False
    stem_extension_eligible: bool = False


class Education(BaseModel):
    id: str
    degree: str
    school: str
    location: str | None = None
    dates: str | None = None
    gpa: float | None = None
    coursework: list[str] = Field(default_factory=list)


class Bullet(BaseModel):
    id: str
    themes: list[str] = Field(default_factory=list)
    text: str
    metrics: list[str] = Field(default_factory=list)
    tech_stack: list[str] = Field(default_factory=list)


class Experience(BaseModel):
    id: str
    title: str
    company: str
    location: str | None = None
    dates: str | None = None
    level: str | None = None  # L1, L2, L3, L4
    bullets: list[Bullet] = Field(default_factory=list)


class Project(BaseModel):
    id: str
    name: str
    subtitle: str | None = None
    stack: list[str] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)
    text: str
    metrics: list[str] = Field(default_factory=list)
    url: str | None = None


class Profile(BaseModel):
    version: int = 1
    personal: PersonalInfo
    visa_status: VisaStatus | None = None
    summary: str | None = None
    education: list[Education] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    skills: dict[str, list[str]] = Field(default_factory=dict)

    def all_bullet_ids(self) -> set[str]:
        """Return all bullet IDs across all experience entries."""
        ids: set[str] = set()
        for exp in self.experience:
            for bullet in exp.bullets:
                ids.add(bullet.id)
        return ids


class FlaggedField(BaseModel):
    path: str
    reason: str


class ExtractionConfidence(BaseModel):
    personal: float = 0.0
    education: float = 0.0
    experience: float = 0.0
    projects: float = 0.0
    skills: float = 0.0


class ParseFromResumeResponse(BaseModel):
    profile: Profile
    extraction_confidence: ExtractionConfidence
    flagged_fields: list[FlaggedField] = Field(default_factory=list)
    raw_extracted_text: str = ""


class ProfileSaveResponse(BaseModel):
    saved: bool
    version: int
