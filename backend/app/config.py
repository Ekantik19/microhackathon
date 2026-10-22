"""Application settings, read from environment variables (and `.env` at the repo root)."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env", ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    # Core
    app_env: str = "local"  # local | azure
    log_level: str = "INFO"
    web_origin: str = "http://localhost:3000"

    # Events
    event_source: str = "local"  # local | fabric
    default_match_id: str = "demo_01"
    data_dir: Path = REPO_ROOT / "data"
    config_dir: Path = REPO_ROOT / "config"

    # AI (Microsoft Foundry)
    ai_provider: str = "mock"  # mock | foundry
    foundry_endpoint: str = ""
    foundry_api_key: str = ""
    foundry_model_deployment: str = "gpt-4.1-mini"
    foundry_api_version: str = ""
    foundry_use_managed_identity: bool = False
    ai_timeout_seconds: float = 8.0

    # Fabric (optional)
    fabric_eventstream_source_connection_string: str = ""
    fabric_eventstream_dest_connection_string: str = ""
    fabric_eventstream_dest_consumer_group: str = "$Default"
    fabric_publish_on_replay: bool = False

    # Database
    database_url: str = "sqlite:///./insidematch.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()
