from types import SimpleNamespace
from uuid import uuid4

from backend import feedback
from db.models import AgentFeedback, AgentTurn, Rating
from langchain_core.documents import Document
from settings import Settings


def test_save_agent_turn_persists_serialized_context(monkeypatch, fake_session) -> None:
    settings = Settings()
    monkeypatch.setattr(feedback, "get_session", lambda _: fake_session)
    session_id = uuid4()
    documents = [
        Document(
            page_content="Refunds are available within 30 days.",
            metadata={"source": "returns.md", "section": "Refunds"},
        )
    ]

    turn_id = feedback.save_agent_turn(
        settings=settings,
        session_id=session_id,
        trace_id="trace-123",
        query="How long do I have to request a refund?",
        answer="Refunds are available within 30 days.",
        context=documents,
    )

    assert turn_id == fake_session.added[0].id
    persisted_turn = fake_session.added[0]
    assert isinstance(persisted_turn, AgentTurn)
    assert persisted_turn.session_id == session_id
    assert persisted_turn.trace_id == "trace-123"
    assert persisted_turn.query == "How long do I have to request a refund?"
    assert persisted_turn.answer == "Refunds are available within 30 days."
    assert persisted_turn.model_name == settings.ollama.llm_model
    assert persisted_turn.retrieved_context == [
        {
            "content": "Refunds are available within 30 days.",
            "metadata": {"source": "returns.md", "section": "Refunds"},
        }
    ]


def test_save_feedback_creates_rating_when_none_exists(
    monkeypatch, fake_session
) -> None:
    monkeypatch.setattr(feedback, "get_session", lambda _: fake_session)
    turn_id = uuid4()
    session_id = uuid4()

    feedback.save_feedback(
        settings=Settings(),
        turn_id=turn_id,
        session_id=session_id,
        rating=Rating.HELPFUL,
    )

    assert len(fake_session.scalar_calls) == 1
    assert len(fake_session.added) == 1
    created_feedback = fake_session.added[0]
    assert isinstance(created_feedback, AgentFeedback)
    assert created_feedback.turn_id == turn_id
    assert created_feedback.session_id == session_id
    assert created_feedback.rating is Rating.HELPFUL


def test_save_feedback_updates_existing_rating(monkeypatch, fake_session) -> None:
    existing_feedback = SimpleNamespace(rating=Rating.HELPFUL)
    fake_session.existing_feedback = existing_feedback
    monkeypatch.setattr(feedback, "get_session", lambda _: fake_session)

    feedback.save_feedback(
        settings=Settings(),
        turn_id=uuid4(),
        session_id=uuid4(),
        rating=Rating.UNHELPFUL,
    )

    assert existing_feedback.rating is Rating.UNHELPFUL
    assert fake_session.added == []
