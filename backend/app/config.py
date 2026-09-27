from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    zane_database_path: Path = Path("backend/zane.db")
    zane_model_provider: str = "none"
    openai_api_key: str | None = None
    zane_openai_model: str = "gpt-4o-mini"


def load_settings() -> Settings:
    return Settings()
