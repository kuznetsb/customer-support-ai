from __future__ import annotations

from uuid import UUID, uuid4

from db.models import AgentFeedback, AgentTurn, Rating
from db.session import get_session
from langchain_core.documents import Document
from settings import Settings
from sqlalchemy import select


def _serialize_context(documents: list[Document]) -> list[dict[str, object]]:
    """Convert retrieved documents into JSON-serializable feedback context."""
    return [
        {
            "content": document.page_content,
            "metadata": {key: str(value) for key, value in document.metadata.items()},
        }
        for document in documents
    ]


def save_agent_turn(
    *,
    settings: Settings,
    session_id: UUID,
    trace_id: str,
    query: str,
    answer: str,
    context: list[Document],
) -> UUID:
    """Persist an answered turn and return its identifier."""
    turn_id = uuid4()
    turn = AgentTurn(
        id=turn_id,
        session_id=session_id,
        trace_id=trace_id,
        query=query,
        answer=answer,
        model_name=settings.ollama.llm_model,
        retrieved_context=_serialize_context(context),
    )
    with get_session(settings) as session:
        session.add(turn)
    return turn_id


def save_feedback(
    *,
    settings: Settings,
    turn_id: UUID,
    session_id: UUID,
    rating: Rating,
) -> None:
    """Create or update the rating for one answered turn."""
    with get_session(settings) as session:
        feedback = session.scalar(
            select(AgentFeedback).where(
                AgentFeedback.turn_id == turn_id,
                AgentFeedback.session_id == session_id,
            )
        )
        if feedback is None:
            session.add(
                AgentFeedback(
                    turn_id=turn_id,
                    session_id=session_id,
                    rating=rating,
                )
            )
        else:
            feedback.rating = rating
