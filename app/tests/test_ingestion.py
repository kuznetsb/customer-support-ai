import ingestion
import pytest
from exceptions import DocumentIngestionError
from langchain_core.documents import Document
from settings import DatabaseSettings, Settings, VectorStoreSettings


def _settings(data_dir) -> Settings:
    return Settings(
        data_dir=data_dir,
        vector_store=VectorStoreSettings(
            collection_name="test-collection",
        ),
        database=DatabaseSettings(url="postgresql://test"),
    )


def test_split_documents_adds_section_context_and_metadata() -> None:
    documents = [
        Document(page_content="# Returns\n## Refunds\nCustomers can request a refund.")
    ]

    chunks = ingestion._split_documents(documents)

    assert len(chunks) == 1
    assert chunks[0].page_content.startswith("Section: Returns > Refunds\n\n")
    assert chunks[0].metadata["section"] == "Returns"
    assert chunks[0].metadata["subsection"] == "Refunds"


def test_ingest_documents_uses_stable_ids(monkeypatch, tmp_path) -> None:
    documents = [
        Document(page_content="first", metadata={"source": "guide.md"}),
        Document(page_content="second", metadata={"source": "guide.md"}),
    ]
    added = {}

    class FakeEmbeddings:
        def __init__(self, **kwargs):
            self.options = kwargs

    class FakePGVector:
        def __init__(self, **kwargs):
            self.options = kwargs

        def add_documents(self, received_documents, ids):
            added["documents"] = received_documents
            added["ids"] = ids

    monkeypatch.setattr(ingestion, "_load_markdown_documents", lambda _: documents)
    monkeypatch.setattr(ingestion, "_split_documents", lambda _: documents)
    monkeypatch.setattr(ingestion, "OllamaEmbeddings", FakeEmbeddings)
    monkeypatch.setattr(ingestion, "PGVector", FakePGVector)

    result = ingestion.ingest_documents(_settings(tmp_path))

    expected_ids = [
        ingestion._document_id(document, index)
        for index, document in enumerate(documents)
    ]
    assert result == 2
    assert added == {"documents": documents, "ids": expected_ids}

    changed_document = Document(page_content="updated", metadata={"source": "guide.md"})
    assert ingestion._document_id(documents[0], 0) == ingestion._document_id(
        changed_document, 0
    )


def test_ingest_documents_returns_zero_without_documents(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(ingestion, "_load_markdown_documents", lambda _: [])

    result = ingestion.ingest_documents(_settings(tmp_path))

    assert result == 0


def test_ingest_documents_wraps_failures(monkeypatch, tmp_path) -> None:
    failure = OSError("cannot read knowledge base")
    monkeypatch.setattr(
        ingestion,
        "_load_markdown_documents",
        lambda _: (_ for _ in ()).throw(failure),
    )

    with pytest.raises(DocumentIngestionError) as error:
        ingestion.ingest_documents(_settings(tmp_path))

    assert str(error.value) == f"Could not ingest documents from {tmp_path}."
    assert error.value.__cause__ is failure
