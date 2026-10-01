import uuid
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base, SoftArchive, Timestamps, UUIDPk


class EvaluationForm(UUIDPk, Timestamps, SoftArchive, Base):
    __tablename__ = "evaluation_forms"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))

    criteria = relationship(
        "EvaluationCriterion",
        back_populates="form",
        order_by="EvaluationCriterion.position",
        lazy="raise",
        cascade="all, delete-orphan",
    )


class EvaluationCriterion(UUIDPk, Timestamps, Base):
    __tablename__ = "evaluation_criteria"

    form_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evaluation_forms.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    weight: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False, default=1, server_default=text("1"))
    max_score: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=5, server_default=text("5"))
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    form = relationship("EvaluationForm", back_populates="criteria", lazy="raise")

    __table_args__ = (
        UniqueConstraint("form_id", "position", name="uq_evaluation_criteria_form_position"),
        CheckConstraint("weight > 0 AND weight <= 10", name="weight"),
        CheckConstraint("max_score IN (5,10)", name="max_score"),
        Index("ix_evaluation_criteria_form_id", "form_id"),
    )


class Evaluation(UUIDPk, Timestamps, SoftArchive, Base):
    __tablename__ = "evaluations"

    form_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("evaluation_forms.id"), nullable=False)
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False
    )
    evaluator_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    overall_comments: Mapped[str | None] = mapped_column(Text)
    recommendation: Mapped[str] = mapped_column(String(16), nullable=False)
    weighted_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    shared_with_student: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )

    form = relationship("EvaluationForm", lazy="raise")
    application = relationship("Application", lazy="raise")
    evaluator = relationship("User", foreign_keys=[evaluator_id], lazy="raise")
    scores = relationship("EvaluationScore", back_populates="evaluation", lazy="raise", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("application_id", "evaluator_id", "form_id", name="uq_evaluations_application_evaluator_form"),
        CheckConstraint("recommendation IN ('STRONG_YES','YES','MAYBE','NO')", name="recommendation"),
        CheckConstraint("weighted_score >= 0 AND weighted_score <= 100", name="weighted_score"),
        Index("ix_evaluations_application_id", "application_id"),
        Index("ix_evaluations_evaluator_id", "evaluator_id"),
    )


class EvaluationScore(Base):
    __tablename__ = "evaluation_scores"

    evaluation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evaluations.id", ondelete="CASCADE"), primary_key=True
    )
    criterion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evaluation_criteria.id"), primary_key=True
    )
    score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)

    evaluation = relationship("Evaluation", back_populates="scores", lazy="raise")
    criterion = relationship("EvaluationCriterion", lazy="raise")

    __table_args__ = (CheckConstraint("score BETWEEN 0 AND 10", name="score"),)
