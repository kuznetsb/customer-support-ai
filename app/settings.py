from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"


class AppBaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class DatabaseSettings(AppBaseSettings):
    url: str = Field(
        default="postgresql+psycopg://rag_user:rag_password@localhost:5432/cs_support_rag",
        validation_alias="DB_URL",
    )


class OllamaSettings(AppBaseSettings):
    base_url: str = Field(
        default="http://localhost:11434", validation_alias="OLLAMA_BASE_URL"
    )
    embedding_model: str = Field(
        default="nomic-embed-text", validation_alias="OLLAMA_EMBEDDING_MODEL"
    )
    llm_model: str = Field(default="llama3.2", validation_alias="OLLAMA_LLM_MODEL")


class VectorStoreSettings(AppBaseSettings):
    collection_name: str = Field(
        default="customer_support_knowledge", validation_alias="PGVECTOR_COLLECTION"
    )


class Settings(AppBaseSettings):
    data_dir: Path = Field(default=DEFAULT_DATA_DIR, validation_alias="DATA_DIR")
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    ollama: OllamaSettings = Field(default_factory=OllamaSettings)
    vector_store: VectorStoreSettings = Field(default_factory=VectorStoreSettings)

    @field_validator("data_dir", mode="before")
    @classmethod
    def resolve_data_dir(cls, value: str | Path | None) -> Path:
        if value is None:
            return DEFAULT_DATA_DIR

        path = Path(value).expanduser()
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        return path.resolve()
