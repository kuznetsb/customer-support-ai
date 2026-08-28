from collections.abc import Iterable
from pathlib import Path

from exceptions import DocumentIngestionError
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langchain_postgres import PGVector
from langchain_text_splitters.markdown import (
    MarkdownHeaderTextSplitter,
    MarkdownTextSplitter,
)
from settings import Settings

CHUNK_SIZE = 700
CHUNK_OVERLAP = 75
SECTION_METADATA_KEYS = ("section", "subsection", "subsection_detail")


def _section_context(document: Document) -> str:
    section_parts = [
        str(document.metadata[key])
        for key in SECTION_METADATA_KEYS
        if document.metadata.get(key)
    ]
    section_reference = " > ".join(section_parts) or "Document preface"
    return f"Section: {section_reference}\n\n"


def _load_markdown_documents(data_dir: Path) -> list[Document]:
    """
    Helper that loads all Markdown files below data_dir and return vector-store documents.
    Args:
        data_dir: The directory to read Markdown files from.
    Returns:
        A list of Document objects created from the Markdown files.
    """
    loader = DirectoryLoader(
        str(data_dir),
        glob="*.md",
        recursive=True,
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
    )
    documents = loader.load()
    return documents


def _split_documents(documents: Iterable[Document]) -> list[Document]:
    """
    Helper that splits documents into chunks of CHUNK_SIZE with CHUNK_OVERLAP.
    Args:
        documents: An iterable of Document objects to be split.
    Returns:
        A list of Document objects that have been split into chunks.
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
    """
    Ingests documents from the specified data directory into the vector store.
    Args:
        settings: An instance of the Settings class containing configuration.
    Returns:
        The number of documents ingested into the vector store.
    """
    try:
        documents = _load_markdown_documents(settings.data_dir)
        if not documents:
            return 0

        documents = _split_documents(documents)

        embeddings = OllamaEmbeddings(
            model=settings.ollama.embedding_model,
            base_url=settings.ollama.base_url,
        )
        vector_store = PGVector(
            embeddings=embeddings,
            collection_name=settings.vector_store.collection_name,
            connection=settings.database.url,
            use_jsonb=True,
        )
        vector_store.add_documents(documents)
        return len(documents)
    except Exception as error:
        raise DocumentIngestionError(
            f"Could not ingest documents from {settings.data_dir}."
        ) from error
