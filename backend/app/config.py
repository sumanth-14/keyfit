from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "development"
    cors_origins: list[str] = ["http://localhost:3000"]

    temp_storage_dir: str = "/tmp/resume_tailor"
    temp_storage_ttl_seconds: int = 600

    nim_base_url: str = "https://integrate.api.nvidia.com/v1"
    use_mock_nim: bool = False

    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:3000/callback"


settings = Settings()
