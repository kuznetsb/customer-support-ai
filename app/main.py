import logging
from uuid import UUID, uuid4

import streamlit as st
from backend.feedback import save_agent_turn, save_feedback
from backend.ingestion import ingest_documents
from backend.retrieval import run_llm
from db.models import Rating
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


def _render_feedback(message: dict, settings: Settings) -> None:
    """Render and persist a thumbs rating for an assistant response."""
    turn_id = message.get("turn_id")
    session_id = message.get("session_id")
    if not turn_id or not session_id:
        return

    rating = st.feedback(
        "thumbs",
        key=f"feedback_{turn_id}",
        disabled=message.get("feedback_submitted", False),
    )
    if rating is None or message.get("feedback_submitted", False):
        return

    selected_rating = Rating.HELPFUL if rating == 1 else Rating.UNHELPFUL
    try:
        save_feedback(
            settings=settings,
            turn_id=UUID(turn_id),
            session_id=UUID(session_id),
            rating=selected_rating,
        )
    except Exception:
        logger.exception("Agent feedback persistence failed")
        st.warning("Your feedback could not be saved.")
    else:
        message["feedback_submitted"] = True
        st.caption("Thanks for your feedback.")


def render_chat_interface(settings: Settings) -> None:
    """Render the chat UI and answer questions with the support agent."""
    st.subheader("Ask the agent a question")
    st.caption("Answers are grounded in the support knowledge base.")

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    if "session_id" not in st.session_state:
        st.session_state.session_id = uuid4()

    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant":
                _render_sources(message.get("context", []))
                _render_feedback(message, settings)

    prompt = st.chat_input("Ask about shipping, returns, or your order...")
    if prompt:
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        trace_id = None
        with st.chat_message("assistant"):
            with st.spinner("Searching the support knowledge base..."):
                try:
                    with trace_context() as trace_id:
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
        assistant_message = {
            "role": "assistant",
            "content": result["answer"],
            "context": result["context"],
        }
        if trace_id is not None:
            try:
                turn_id = save_agent_turn(
                    settings=settings,
                    session_id=st.session_state.session_id,
                    trace_id=trace_id,
                    query=prompt,
                    answer=result["answer"],
                    context=result["context"],
                )
            except Exception:
                logger.exception("Agent turn persistence failed")
            else:
                assistant_message["turn_id"] = str(turn_id)
                assistant_message["session_id"] = str(st.session_state.session_id)
        st.session_state.chat_messages.append(assistant_message)
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
