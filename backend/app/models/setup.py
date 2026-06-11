from pydantic import BaseModel


class SetupResponse(BaseModel):
    folder_id: str
    subfolders_created: list[str]
    ready: bool
