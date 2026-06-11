from pydantic import BaseModel, Field


class RoleConfig(BaseModel):
    version: int = 1
    role_id: str
    role_display_name: str
    source: str = "auto_generated"  # "built_in" | "auto_generated" | "user_edited"
    generated_at: str | None = None
    skills_order: list[str] = Field(default_factory=list)
    bullet_priority_strategy: str = ""
    project_priority_strategy: str = ""
    summary_focus: str = ""
    keywords_emphasis: list[str] = Field(default_factory=list)
    preferred_action_verbs: list[str] = Field(default_factory=list)
