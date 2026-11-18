"""Application configuration management using Pydantic Settings."""

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global configuration settings for the Autonomous Data Analyst AI application."""

    # LLM Settings
    openai_api_key: Optional[str] = Field(
        default=None,
        description="OpenAI API key. If not provided, fallback heuristic/rule-based responses are used where applicable."
    )
    openai_model: str = Field(
        default="gpt-4o-mini",
        description="Configurable OpenAI model name (e.g., gpt-4o, gpt-4o-mini, o3-mini)."
    )
    openai_api_base: Optional[str] = Field(
        default=None,
        description="Custom OpenAI API base URL if using compatible proxies or local endpoints."
    )
    openai_temperature: float = Field(
        default=0.1,
        description="Sampling temperature for the LLM."
    )

    # Execution Sandbox Settings
    sandbox_type: str = Field(
        default="secure_subprocess",
        description="Execution sandbox provider: isolated secure out-of-process subprocess runner."
    )
    sandbox_timeout_seconds: int = Field(
        default=30,
        description="Maximum execution timeout in seconds for generated Python code."
    )
    sandbox_max_memory_mb: int = Field(
        default=512,
        description="Maximum allowed memory in megabytes for the sandbox container or subprocess."
    )
    sandbox_max_cpu_percent: int = Field(
        default=80,
        description="Maximum CPU percentage allowed."
    )
    max_correction_retries: int = Field(
        default=3,
        description="Maximum number of self-correction attempts when code execution fails."
    )

    # Storage & Paths
    storage_path: Path = Field(
        default=Path("./data"),
        description="Root directory for application data."
    )
    database_url: str = Field(
        default="sqlite:///./data/autonomous_analyst.db",
        description="Database URL for session and analysis persistence."
    )

    # Observability
    log_level: str = Field(
        default="INFO",
        description="Application logging level (DEBUG, INFO, WARNING, ERROR)."
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def uploads_path(self) -> Path:
        """Directory for uploaded datasets."""
        p = self.storage_path / "uploads"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def samples_path(self) -> Path:
        """Directory for bundled sample datasets."""
        p = self.storage_path / "samples"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def reports_path(self) -> Path:
        """Directory for exported analytical reports."""
        p = Path("./reports")
        p.mkdir(parents=True, exist_ok=True)
        return p


@lru_cache()
def get_settings() -> Settings:
    """Retrieve cached instance of application settings."""
    return Settings()
