import hashlib
import logging
from collections.abc import Iterable
from pathlib import Path

from dependencies.vector_store import get_vector_store_for_settings
from exceptions import DocumentIngestionError
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_core.documents import Document
from langchain_text_splitters.markdown import (
    MarkdownHeaderTextSplitter,
    MarkdownTextSplitter,
)
from settings import Settings

CHUNK_SIZE = 700
CHUNK_OVERLAP = 75
SECTION_METADATA_KEYS = ("section", "subsection", "subsection_detail")
logger = logging.getLogger(__name__)


def _document_id(document: Document, index: int) -> str:
    """Return a stable identifier for a document's source and position.

    Args:
        document: Document whose source metadata is used to build the ID.
        index: Position of the document in the ingestion batch.

    Returns:
        A SHA-256 hexadecimal identifier.
    """
    source = str(document.metadata.get("source", ""))
    return hashlib.sha256(f"{source}:{index}".encode()).hexdigest()


def _section_context(document: Document) -> str:
    """Build the section heading context prefixed to a document chunk.

    Args:
        document: Document containing section metadata.

    Returns:
        A formatted section reference, or a document preface marker.
    """
    section_parts = [
        str(document.metadata[key])
        for key in SECTION_METADATA_KEYS
        if document.metadata.get(key)
    ]
    section_reference = " > ".join(section_parts) or "Document preface"
    return f"Section: {section_reference}\n\n"


def _load_markdown_documents(data_dir: Path) -> list[Document]:
    """Load Markdown documents recursively from a data directory.

    Args:
        data_dir: Directory containing the Markdown knowledge base.

    Returns:
        The loaded Markdown documents.
    """
    loader = DirectoryLoader(
        str(data_dir),
        glob="*.md",
        recursive=True,
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
    )
    return loader.load()


def _split_documents(documents: Iterable[Document]) -> list[Document]:
    """Split documents into context-preserving chunks for vector storage.

    Args:
        documents: Documents to split by Markdown headings and chunk size.

    Returns:
        Chunked documents with section context and inherited metadata.
    """
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[
            ("#", "section"),
            ("##", "subsection"),
            ("###", "subsection_detail"),
        ],
        strip_headers=True,
    )
    section_documents = []
    for document in documents:
        for section_document in header_splitter.split_text(document.page_content):
            section_document.metadata.update(document.metadata)
            section_documents.append(section_document)

    chunks = []
    for section_document in section_documents:
        section_context = _section_context(section_document)
        content_chunk_size = CHUNK_SIZE - len(section_context)
        content_chunk_overlap = min(CHUNK_OVERLAP, content_chunk_size // 3)
        chunk_splitter = MarkdownTextSplitter(
            chunk_size=content_chunk_size,
            chunk_overlap=content_chunk_overlap,
            length_function=len,
        )
        for chunk in chunk_splitter.split_documents([section_document]):
            chunks.append(
                Document(
                    page_content=section_context + chunk.page_content,
                    metadata=chunk.metadata,
                )
            )
    return chunks


def ingest_documents(settings: Settings) -> int:
    """Ingest Markdown knowledge-base documents into the vector store.

    Args:
        settings: Application settings containing the data directory and vector
            store configuration.

    Returns:
        The number of document chunks ingested, or zero when no documents exist.

    Raises:
        DocumentIngestionError: If loading, splitting, or storing documents fails.
    """
    logger.info("Starting knowledge-base ingestion from %s", settings.data_dir)
    try:
        documents = _load_markdown_documents(settings.data_dir)
        if not documents:
            logger.info("No Markdown documents found for knowledge-base ingestion")
            return 0

        documents = _split_documents(documents)
        logger.info("Prepared %d document chunks for vector storage", len(documents))

        vector_store = get_vector_store_for_settings(settings)
        vector_store.add_documents(
            documents,
            ids=[
                _document_id(document, index)
                for index, document in enumerate(documents)
            ],
        )
        logger.info("Knowledge-base ingestion completed: %d chunks", len(documents))
        return len(documents)
    except Exception as error:
        logger.exception("Knowledge-base ingestion failed")
        raise DocumentIngestionError(
            f"Could not ingest documents from {settings.data_dir}."
        ) from error
