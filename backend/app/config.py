import json
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "development"
    # NoDecode disables pydantic-settings' automatic JSON decoding of the raw
    # env value, so the validator below can accept a JSON list, a comma-separated
    # string, or a single bare URL — whichever way the host's dashboard saved it.
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value: object) -> list[str]:
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return []
            origins = json.loads(value) if value.startswith("[") else value.split(",")
        else:
            origins = value  # already a list (e.g. the default)
        if not isinstance(origins, list):
            return origins
        # Browser Origin headers never carry a trailing slash, so strip any the
        # operator left on a dashboard value — otherwise CORS silently fails.
        return [o.strip().rstrip("/") for o in origins if str(o).strip()]

    temp_storage_dir: str = "/tmp/resume_tailor"
    temp_storage_ttl_seconds: int = 600

    nim_base_url: str = "https://integrate.api.nvidia.com/v1"
    use_mock_nim: bool = False
    # Resume parsing is mechanical extraction, not reasoning — a small fast model
    # keeps it under the 30s UX budget. Override via env without a code change.
    nim_parser_model: str = "meta/llama-3.1-8b-instruct"

    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:3000/callback"


settings = Settings()
