from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    database_url: str
    jwt_secret: str = Field(min_length=32)
    jwt_expire_minutes: int = Field(default=720,ge=1,le=10080)
    gemini_api_key: str | None = None
    gemini_model: str = ""
    demo_mode: bool = False
    allowed_origins: str = ""
    max_upload_mb: int = Field(default=5,ge=1,le=20)
    enable_semantic: bool = False
    # Neon CLI writes service credentials to .env.local. Load normal local
    # settings first, then allow the Neon-generated values to override them.
    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", PROJECT_ROOT.parent / ".env", PROJECT_ROOT / ".env.local"),
        extra="ignore",
        case_sensitive=False,
    )

    @property
    def cors_origins(self):
        origins = [x.strip() for x in self.allowed_origins.split(",") if x.strip()]
        if self.demo_mode:
            origins += ["http://localhost:5173", "http://localhost:3000"]
        return list(dict.fromkeys(origins))


settings = Settings()


# Role B transports intentionally use environment configuration. Pydantic loads
# local .env settings without exporting them, so bridge explicitly at startup.
import os
if settings.gemini_api_key: os.environ.setdefault('GEMINI_API_KEY', settings.gemini_api_key)
if settings.gemini_model: os.environ.setdefault('GEMINI_MODEL', settings.gemini_model)
