"""Configuration management with Pydantic Settings."""

from __future__ import annotations

import secrets
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with layered configuration."""

    # Application
    app_name: str = "NVIDIA Multi-Agent Builder"
    app_version: str = "0.1.0"
    environment: Literal["development", "staging", "production", "testing"] = "development"
    debug: bool = False

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 1
    api_reload: bool = False

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/app.db"
    database_echo: bool = False
    database_pool_size: int = 5
    database_max_overflow: int = 10

    # Redis (for Celery, caching, pub/sub)
    redis_url: str = "redis://localhost:6379/0"

    # Model Providers
    nvidia_api_key: SecretStr | None = None
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    openai_api_key: SecretStr | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    local_model_path: str = "./models"

    # Model Registry
    model_registry_path: str = "./config/model_registry.yaml"

    # Sandbox
    sandbox_type: Literal["docker", "process", "none"] = "docker"
    docker_image: str = "python:3.11-slim"
    sandbox_timeout: int = 30
    sandbox_memory_limit: str = "512m"
    sandbox_cpu_limit: float = 1.0

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_format: Literal["json", "console"] = "json"
    log_file: str | None = None

    # Security
    secret_key: SecretStr = Field(
        default_factory=lambda: SecretStr(secrets.token_urlsafe(32))
    )
    access_token_expire_minutes: int = 30
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:5173"]
    )

    # Observability
    otel_endpoint: str | None = None
    otel_service_name: str = "nvidia-multi-agent-builder"
    prometheus_port: int = 9090

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_nested_delimiter="__",
    )

    @property
    def data_dir(self) -> Path:
        """Get data directory path."""
        db_path = self.database_url.replace("sqlite+aiosqlite:///", "").replace("sqlite:///", "")
        return Path(db_path).parent

    def validate_providers(self) -> list[str]:
        """Validate at least one model provider is configured."""
        errors = []
        if not self.nvidia_api_key and not self.openai_api_key:
            errors.append("At least one model provider API key required (NVIDIA_API_KEY or OPENAI_API_KEY)")
        return errors


# Global settings instance
settings = Settings()