import pytest
from dependencies.vector_store import get_embeddings, get_vector_store


class FakeSession:
    def __init__(self, existing_feedback=None):
        self.existing_feedback = existing_feedback
        self.added = []
        self.scalar_calls = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def add(self, value):
        self.added.append(value)

    def scalar(self, statement):
        self.scalar_calls.append(statement)
        return self.existing_feedback


@pytest.fixture
def fake_session() -> FakeSession:
    return FakeSession()


@pytest.fixture(autouse=True)
def clear_vector_store_cache():
    get_embeddings.cache_clear()
    get_vector_store.cache_clear()
    yield
    get_embeddings.cache_clear()
    get_vector_store.cache_clear()
