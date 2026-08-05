from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SahiSehat AI"
    app_env: str = "development"

    host: str = "0.0.0.0"
    port: int = 8000

    gemini_api_key: str
    gemini_model: str = "gemini-3.5-flash"

    sahisehat_backend_url: str = "http://localhost:4000/api"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()