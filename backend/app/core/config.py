from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="SE-Agent Studio API", alias="APP_NAME")
    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")
    database_url: str = Field(default="sqlite:///./.runtime/se_agent_studio.db", alias="DATABASE_URL")
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_base_url: str = Field(default="https://api.openai.com/v1", alias="OPENAI_BASE_URL")
    default_model: str = Field(default="gpt-4.1-mini", alias="DEFAULT_MODEL")
    jwt_secret: str = Field(default="change-me", alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=720, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    execution_mode: str = Field(default="local", alias="EXECUTION_MODE")
    agent_runtime_mode: str = Field(default="auto", alias="AGENT_RUNTIME_MODE")
    llm_timeout_seconds: int = Field(default=120, alias="LLM_TIMEOUT_SECONDS")
    auto_create_schema: bool = Field(default=True, alias="AUTO_CREATE_SCHEMA")
    cors_origins: List[str] = Field(default_factory=lambda: ["http://localhost:5173"], alias="CORS_ORIGINS")
    default_owner_email: str = Field(default="demo@se-agent.studio", alias="DEFAULT_OWNER_EMAIL")
    default_owner_name: str = Field(default="Demo User", alias="DEFAULT_OWNER_NAME")
    default_owner_password: str = Field(default="ChangeMe123!", alias="DEFAULT_OWNER_PASSWORD")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", populate_by_name=True)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value):  # type: ignore[no-untyped-def]
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("agent_runtime_mode")
    @classmethod
    def validate_agent_runtime_mode(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"auto", "template", "crewai"}:
            raise ValueError("AGENT_RUNTIME_MODE must be one of: auto, template, crewai")
        return normalized

    @property
    def has_ai_runtime_config(self) -> bool:
        if self.openai_api_key.strip():
            return True
        return self.openai_base_url.strip() not in {"", "https://api.openai.com/v1"}

    @property
    def backend_root(self) -> Path:
        return Path(__file__).resolve().parents[2]

    @property
    def repo_root(self) -> Path:
        return Path(__file__).resolve().parents[3]

    @property
    def runtime_dir(self) -> Path:
        path = self.backend_root / ".runtime"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def agents_dir(self) -> Path:
        return self.repo_root / "agents"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
