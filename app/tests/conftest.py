import pytest
from dependencies.vector_store import get_embeddings, get_vector_store


@pytest.fixture(autouse=True)
def clear_vector_store_cache():
    get_embeddings.cache_clear()
    get_vector_store.cache_clear()
    yield
    get_embeddings.cache_clear()
    get_vector_store.cache_clear()
