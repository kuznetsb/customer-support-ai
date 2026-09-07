from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from db.base import Base
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

FEEDBACK_SCHEMA = "feedback"


class Rating(str, Enum):
    HELPFUL = "helpful"
    UNHELPFUL = "unhelpful"


class AgentTurn(Base):
    __tablename__ = "agent_turns"
    __table_args__ = (
        Index("ix_agent_turns_created_at", "created_at"),
        {"schema": FEEDBACK_SCHEMA},
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    session_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    trace_id: Mapped[str] = mapped_column(String(128), nullable=False)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    retrieved_context: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    feedback: Mapped[list[AgentFeedback]] = relationship(
        back_populates="turn", cascade="all, delete-orphan"
    )


class AgentFeedback(Base):
    __tablename__ = "agent_feedback"
    __table_args__ = (
        UniqueConstraint(
            "turn_id", "session_id", name="uq_agent_feedback_turn_session"
        ),
        Index("ix_agent_feedback_created_at", "created_at"),
        Index("ix_agent_feedback_rating", "rating"),
        {"schema": FEEDBACK_SCHEMA},
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    turn_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(
            f"{FEEDBACK_SCHEMA}.agent_turns.id",
            name="fk_agent_feedback_turn_id_agent_turns",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    turn: Mapped[AgentTurn] = relationship(back_populates="feedback")
    session_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    rating: Mapped[Rating] = mapped_column(
        SQLEnum(
            Rating,
            name="feedback_rating",
            schema=FEEDBACK_SCHEMA,
            values_callable=lambda enum: [member.value for member in enum],
            validate_strings=True,
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        server_default=func.now(),
    )
