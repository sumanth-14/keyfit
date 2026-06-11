from pydantic import BaseModel, Field


class OutreachMessages(BaseModel):
    cold_email_subject: str = ""
    cold_email_body: str = ""
    linkedin_connection_note: str = ""
    linkedin_inmail_subject: str = ""
    linkedin_inmail_body: str = ""


class OutreachJson(BaseModel):
    version: int = 1
    company: str
    role_title: str
    generated_at: str
    messages: OutreachMessages = Field(default_factory=OutreachMessages)
    personalization_used: list[str] = Field(default_factory=list)
