from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"


def _resolve_path(value: str | None, default: Path) -> Path:
    if value is None:
        return default

    path = Path(value).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


@dataclass(frozen=True)
class DatabaseSettings:
    url: str = (
        "postgresql+psycopg://rag_user:rag_password@localhost:5432/cs_support_rag"
    )

    @classmethod
    def from_env(cls) -> DatabaseSettings:
        return cls(url=os.getenv("DB_URL", cls.url))


@dataclass(frozen=True)
class OllamaSettings:
    base_url: str = "http://localhost:11434"
    embedding_model: str = "nomic-embed-text"

    @classmethod
    def from_env(cls) -> OllamaSettings:
        return cls(
            base_url=os.getenv("OLLAMA_BASE_URL", cls.base_url),
            embedding_model=os.getenv("OLLAMA_EMBEDDING_MODEL", cls.embedding_model),
        )


@dataclass(frozen=True)
class VectorStoreSettings:
    collection_name: str = "customer_support_knowledge"

    @classmethod
    def from_env(cls) -> VectorStoreSettings:
        return cls(
            collection_name=os.getenv("PGVECTOR_COLLECTION", cls.collection_name)
        )


@dataclass(frozen=True)
class Settings:
    data_dir: Path = DEFAULT_DATA_DIR
    database: DatabaseSettings = DatabaseSettings()
    ollama: OllamaSettings = OllamaSettings()
    vector_store: VectorStoreSettings = VectorStoreSettings()

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            data_dir=_resolve_path(os.getenv("DATA_DIR"), DEFAULT_DATA_DIR),
            database=DatabaseSettings.from_env(),
            ollama=OllamaSettings.from_env(),
            vector_store=VectorStoreSettings.from_env(),
        )
