"""Evaluation schemas (plan 6.7). weighted_score = 100 * sum(score/max_score * weight) / sum(weight)."""

import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.types import Money

Recommendation = Literal["STRONG_YES", "YES", "MAYBE", "NO"]
MaxScore = Literal[5, 10]
Weight = Annotated[float, Field(gt=0, le=10)]


class EvaluationCriterion(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None = None
    weight: float
    max_score: MaxScore
    position: int


class EvaluationForm(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None = None
    is_default: bool
    criteria: list[EvaluationCriterion]
    archived_at: datetime | None = None
    created_at: datetime
    in_use: bool


class CriterionInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    weight: Weight
    max_score: MaxScore


def _unique_names(criteria: list[CriterionInput]) -> list[CriterionInput]:
    names = [c.name.lower() for c in criteria]
    if len(set(names)) != len(names):
        raise ValueError("Criterion names must be unique within a form")
    return criteria


class EvaluationFormCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    criteria: list[CriterionInput] = Field(min_length=1, max_length=20)

    @field_validator("criteria")
    @classmethod
    def _names(cls, v: list[CriterionInput]) -> list[CriterionInput]:
        return _unique_names(v)


class EvaluationFormUpdateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    criteria: list[CriterionInput] | None = Field(default=None, min_length=1, max_length=20)

    @field_validator("criteria")
    @classmethod
    def _names(cls, v: list[CriterionInput] | None) -> list[CriterionInput] | None:
        return _unique_names(v) if v is not None else v


class EvaluationSummary(BaseModel):
    id: uuid.UUID
    form_name: str
    evaluator_name: str
    weighted_score: Money
    recommendation: Recommendation
    created_at: datetime
    shared_with_student: bool


class PersonRef(BaseModel):
    id: uuid.UUID
    full_name: str


class InternshipRef(BaseModel):
    id: uuid.UUID
    title: str


class EvaluationScoreOut(BaseModel):
    criterion_id: uuid.UUID
    criterion_name: str
    score: int
    max_score: int
    weight: float
    comment: str | None = None


class Evaluation(EvaluationSummary):
    form_id: uuid.UUID
    application_id: uuid.UUID
    student: PersonRef
    internship: InternshipRef
    scores: list[EvaluationScoreOut]
    overall_comments: str | None = None
    archived_at: datetime | None = None


class ScoreInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    criterion_id: uuid.UUID
    score: int = Field(ge=0, le=10)
    comment: str | None = Field(default=None, max_length=2000)


class EvaluationCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    form_id: uuid.UUID
    application_id: uuid.UUID
    scores: list[ScoreInput] = Field(min_length=1)
    overall_comments: str | None = Field(default=None, max_length=5000)
    recommendation: Recommendation
    shared_with_student: bool = False


class EvaluationUpdateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    scores: list[ScoreInput] | None = Field(default=None, min_length=1)
    overall_comments: str | None = Field(default=None, max_length=5000)
    recommendation: Recommendation | None = None
    shared_with_student: bool | None = None
