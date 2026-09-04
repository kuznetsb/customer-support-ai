import logging

import streamlit as st
from backend.ingestion import ingest_documents
from backend.retrieval import run_llm
from exceptions import DocumentIngestionError
from langchain_core.documents import Document
from logging_config import configure_logging, trace_context
from settings import Settings

logger = logging.getLogger(__name__)


@st.cache_resource
def load_knowledge_base() -> int:
    """Ingest the knowledge base once for the lifetime of the app process."""
    return ingest_documents(Settings())


def _render_sources(documents: list[Document]) -> None:
    """Render the documents retrieved for an assistant response."""
    if not documents:
        return

    with st.expander(f"Sources ({len(documents)})"):
        for document in documents:
            section, separator, content = document.page_content.partition("\n\n")
            if section.startswith("Section: "):
                st.caption(section)
            else:
                content = document.page_content
            st.markdown(content if separator else document.page_content)


def render_chat_interface(settings: Settings) -> None:
    """Render the chat UI and answer questions with the support agent."""
    st.subheader("Ask the agent a question")
    st.caption("Answers are grounded in the support knowledge base.")

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant":
                _render_sources(message.get("context", []))

    prompt = st.chat_input("Ask about shipping, returns, or your order...")
    if prompt:
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("assistant"):
            with st.spinner("Searching the support knowledge base..."):
                try:
                    result = run_llm(prompt, settings)
                except Exception:
                    logger.exception("Support agent request failed")
                    st.error("The support agent is temporarily unavailable.")
                    result = {
                        "answer": "I couldn't complete that request. Please try again.",
                        "context": [],
                    }
            st.markdown(result["answer"])
            _render_sources(result["context"])
        st.session_state.chat_messages.append(
            {
                "role": "assistant",
                "content": result["answer"],
                "context": result["context"],
            }
        )
        st.rerun()


def main() -> None:
    settings = Settings()
    configure_logging(settings.log_level)
    logger.info("Starting Customer Support AI")
    st.set_page_config(page_title="Customer Support AI", page_icon=":speech_balloon:")
    st.title("Customer Support AI")

    with st.status("Loading knowledge base...", expanded=True) as status:
        st.write("Reading support documents and creating embeddings.")
        with trace_context():
            logger.info("Loading knowledge base")
            try:
                chunk_count = load_knowledge_base()
            except DocumentIngestionError as error:
                logger.error("Knowledge base failed to load")
                status.update(label="Knowledge base failed to load", state="error")
                st.error(str(error))
                with st.expander("Technical details"):
                    st.exception(error.__cause__ or error)
                st.stop()
            logger.info("Knowledge base ready: %d chunks", chunk_count)

        status.update(label="Knowledge base ready", state="complete")

    st.success(f"Loaded {chunk_count} document chunks.")

    if "chat_open" not in st.session_state:
        st.session_state.chat_open = False

    if not st.session_state.chat_open:
        st.write("Get help from the support agent using your knowledge base.")
        if st.button(
            "Ask the agent a question", type="primary", icon=":material/chat:"
        ):
            st.session_state.chat_open = True
            st.rerun()
    else:
        if st.button("Close chat", icon=":material/close:"):
            st.session_state.chat_open = False
            st.rerun()
        render_chat_interface(settings)


if __name__ == "__main__":
    main()
