from enum import Enum
from pathlib import Path
from typing import Tuple

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    DEVELOPMENT = "development"
    QA = "qa"
    PRODUCTION = "production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Environment = Environment.DEVELOPMENT

    # LLM
    openrouter_api_key: str = ""
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    model: str = "deepseek/deepseek-chat"
    embedding_model: str = "text-embedding-3-small"
    model_provider: str = "openrouter"

    # Discord
    discord_token: str = ""

    # Database
    database_url: str = "sqlite+aiosqlite:///./qa_copilot.db"

    # Auth
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    # Admin bootstrap credentials
    admin_username: str = "admin"
    admin_password: str = "admin"
    admin_email: str = "admin@example.com"

    # Logging
    log_level: str = "INFO"

    # Rate limiting
    rate_limit_per_minute: int = 60

    # Upload
    max_upload_bytes: int = 50 * 1024 * 1024  # 50 MB
    allowed_upload_extensions: Tuple[str, ...] = (
        ".pdf",
        ".docx",
        ".txt",
        ".md",
        ".json",
        ".yaml",
        ".yml",
        ".sql",
        ".png",
        ".jpg",
        ".jpeg",
        ".feature",
        ".postman_collection.json",
    )

    # CORS
    cors_origins: str = "*"

    @field_validator("jwt_secret_key")
    @classmethod
    def jwt_secret_must_be_set(cls, v: str) -> str:
        if v == "change-me-in-production":
            import warnings
            warnings.warn(
                "JWT_SECRET_KEY is using the default insecure value. Set it in .env for production."
            )
        return v

    @property
    def base_path(self) -> Path:
        return Path(__file__).resolve().parent.parent

    @property
    def prompts_path(self) -> Path:
        return self.base_path / "prompts"

    @property
    def knowledge_path(self) -> Path:
        return self.base_path / "knowledge"

    @property
    def uploads_path(self) -> Path:
        return self.base_path / "uploads"

    @property
    def frontend_path(self) -> Path:
        return self.base_path / "frontend"

    @property
    def logs_path(self) -> Path:
        return self.base_path / "logs"

    @property
    def reports_path(self) -> Path:
        return self.base_path / "reports"

    @property
    def agent_names(self) -> Tuple[str, ...]:
        return (
            "analyst",
            "developer",
            "tester",
            "automation",
            "sql",
            "documentation",
            "bug_investigator",
            "security_reviewer",
            "performance_engineer",
        )

    @property
    def is_production(self) -> bool:
        return self.environment == Environment.PRODUCTION

    @property
    def cors_origins_list(self) -> list[str]:
        if self.cors_origins == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",")]


settings = Settings()
