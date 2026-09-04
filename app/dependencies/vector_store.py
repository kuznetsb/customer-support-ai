from functools import cache

from langchain_ollama import OllamaEmbeddings
from langchain_postgres import PGVector
from settings import Settings


@cache
def get_embeddings(settings_key: tuple[str, str]) -> OllamaEmbeddings:
    base_url, embedding_model = settings_key
    return OllamaEmbeddings(model=embedding_model, base_url=base_url)


@cache
def get_vector_store(
    settings_key: tuple[str, str, str, str],
) -> PGVector:
    connection, collection_name, base_url, embedding_model = settings_key
    embeddings = get_embeddings((base_url, embedding_model))
    return PGVector(
        embeddings=embeddings,
        collection_name=collection_name,
        connection=connection,
        use_jsonb=True,
    )


def get_vector_store_for_settings(settings: Settings) -> PGVector:
    key = (
        settings.database.url,
        settings.vector_store.collection_name,
        settings.ollama.base_url,
        settings.ollama.embedding_model,
    )
    return get_vector_store(key)
