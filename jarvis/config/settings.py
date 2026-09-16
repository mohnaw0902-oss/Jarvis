"""Typed application settings loaded exclusively from environment variables."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. Empty credentials intentionally disable remote LLM calls."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="JARVIS_", extra="ignore")
    app_name: str = "JARVIS"
    environment: Literal["development", "test", "production"] = "development"
    database_url: str = "sqlite+aiosqlite:///./jarvis.db"
    llm_provider: str = "openai_compatible"
    llm_model: str = ""
    llm_base_url: str = ""
    llm_api_key: SecretStr | None = None
    llm_temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    tool_rate_limit_per_minute: int = Field(default=30, ge=1, le=600)
    workspace_root: Path = Path(".")
    max_file_read_bytes: int = Field(default=1_000_000, ge=1, le=10_000_000)
    log_level: str = "INFO"
