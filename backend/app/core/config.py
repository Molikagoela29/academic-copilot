from functools import lru_cache
from pathlib import Path
from typing import Annotated, List

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# backend/ directory — all relative storage paths are anchored here so the app
# behaves identically no matter which directory uvicorn is launched from.
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── LLM ───────────────────────────────────────────────────────────────
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"
    llm_timeout: float = 180.0
    llm_connect_timeout: float = 5.0
    llm_temperature: float = 0.2

    # ── Embeddings / retrieval ────────────────────────────────────────────
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_batch_size: int = 64
    chunk_size: int = 1000
    chunk_overlap: int = 150
    retrieval_k: int = 6
    min_similarity: float = 0.25

    # ── Uploads ───────────────────────────────────────────────────────────
    max_upload_bytes: int = 50 * 1024 * 1024  # 50 MB
    max_pages: int = 1500

    # ── Storage ───────────────────────────────────────────────────────────
    data_dir: Path = BACKEND_DIR / "data"

    # ── Server ────────────────────────────────────────────────────────────
    # NoDecode keeps pydantic-settings from JSON-parsing the raw env value, so
    # the comma-separated form below reaches _split_origins intact.
    cors_origins: Annotated[List[str], NoDecode] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    log_level: str = "INFO"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value):
        """Allow CORS_ORIGINS to be given as a comma-separated string in .env."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def upload_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def storage_dir(self) -> Path:
        return self.data_dir / "storage"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "copilot.db"

    @property
    def ollama_generate_url(self) -> str:
        return f"{self.ollama_url.rstrip('/')}/api/generate"

    @property
    def ollama_tags_url(self) -> str:
        return f"{self.ollama_url.rstrip('/')}/api/tags"

    def ensure_dirs(self) -> None:
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.storage_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
