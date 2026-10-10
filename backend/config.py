"""
Central application configuration loaded from environment variables (.env).
Never hard-code secrets here.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    env: str = "development"
    app_port: int = 8000
    cors_origins: str = "http://localhost:3000"

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/policygraph"
    sync_database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/policygraph"

    llm_provider: str = "ollama"
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    groq_api_key: str | None = None
    gemini_api_key: str | None = None
    llm_model: str = "llama3.2"
    ollama_base_url: str = "http://localhost:11434"

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dim: int = 384

    upload_dir: str = "./uploads"
    max_upload_mb: int = 25

    enable_ocr: bool = False
    tesseract_cmd: str = "/usr/bin/tesseract"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
