"""Runtime config pulled from environment variables.

The demo's 12-factor surface: everything that differs between local
docker-compose and the GCP VM lives here.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ─── Vertex AI ────────────────────────────────────────────
    vertex_project_id: str = Field(default="", alias="VERTEX_PROJECT_ID")
    vertex_location: str = Field(default="us-central1", alias="DEFAULT_VERTEX_AI_LOCATION")
    # Default model name; may carry a `google/` prefix (LiteLLM-style) — stripped before use.
    vertex_model: str = Field(
        default="gemini-2.5-flash-lite",
        alias="DEFAULT_VERTEX_AI_MODEL",
    )
    google_application_credentials: str = Field(
        default="", alias="GOOGLE_APPLICATION_CREDENTIALS"
    )

    # ─── Data services ───────────────────────────────────────
    qdrant_url: str = Field(default="http://qdrant:6333", alias="QDRANT_URL")
    neo4j_uri: str = Field(default="bolt://neo4j:7687", alias="NEO4J_URI")
    neo4j_user: str = Field(default="neo4j", alias="NEO4J_USER")
    neo4j_password: str = Field(default="rag-pitfalls-demo", alias="NEO4J_PASSWORD")
    postgres_dsn: str = Field(
        default="postgresql://demo:demo@postgres:5432/demo",
        alias="POSTGRES_DSN",
    )
    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")

    # ─── Embedder (HF Text Embeddings Inference, BGE-M3) ─────
    embedder_url: str = Field(default="http://embedder:80", alias="EMBEDDER_URL")
    embedder_model: str = Field(default="BAAI/bge-m3", alias="EMBEDDER_MODEL")
    hf_token: str = Field(default="", alias="HF_TOKEN")

    # ─── Demo runtime knobs ──────────────────────────────────
    memory_window_size: int = Field(default=5, alias="MEMORY_WINDOW_SIZE")
    rag_version_cap: int = Field(default=10, alias="RAG_VERSION_CAP")
    cors_origins: str = Field(default="*", alias="CORS_ORIGINS")

    # Paths inside the container. Resolved relative to this file.
    @property
    def project_root(self) -> Path:
        return Path(__file__).resolve().parent.parent

    @property
    def rag_live_path(self) -> Path:
        return self.project_root / "app" / "core" / "rag.py"

    @property
    def rag_default_path(self) -> Path:
        return self.project_root / "app" / "core" / "rag.py.default"

    @property
    def scenarios_root(self) -> Path:
        return self.project_root / "app" / "scenarios"

    def resolve_vertex_model(self) -> str:
        """Strip `google/` LiteLLM-style prefix if present."""
        name = self.vertex_model
        if "/" in name:
            name = name.split("/", 1)[1]
        return name


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
