from pydantic import BaseModel


class CompileRequest(BaseModel):
    tex_source: str
    filename_hint: str = "resume"


class CompileError(BaseModel):
    line: int | None = None
    type: str
    message: str


class CompileResponse(BaseModel):
    success: bool
    # Success fields
    pdf_id: str | None = None
    pdf_url: str | None = None
    pages: int | None = None
    warnings: list[str] = []
    expires_at: str | None = None
    # Failure fields
    errors: list[CompileError] = []
    compile_log: str | None = None
