"""Pydantic v2 models: Job, ScoreResult, WorkflowRun, JobStatus."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class JobStatus(StrEnum):
    """The only idempotency mechanism. Three states, forever (SPEC.md Decision 4)."""

    NEW = "NEW"
    SCORED = "SCORED"
    NOTIFIED = "NOTIFIED"


class Job(BaseModel):
    guid: str = Field(min_length=1)
    source: str = "freelancer"
    url: str | None = None
    title: str | None = None
    description: str = ""  # plain text — HTML stripped at ingest
    score: int | None = Field(default=None, ge=1, le=10)
    reasoning: str | None = None
    status: JobStatus = JobStatus.NEW
    score_attempts: int = Field(default=0, ge=0)
    fetched_at: datetime
    scored_at: datetime | None = None
    notified_at: datetime | None = None


class ScoreResult(BaseModel):
    """Structured output schema for scoring. Client-side Pydantic validation is
    the real gate — the API strips numeric bounds server-side (Decision 6)."""

    score: int = Field(ge=1, le=10)
    reasoning: str


class StageError(BaseModel):
    """One entry of workflow_runs.errors. Messages must already be sanitized
    (Decision 19) — this model stores whatever it is given."""

    stage: str
    type: str
    message: str


class WorkflowRun(BaseModel):
    id: str | None = None
    started_at: datetime
    finished_at: datetime | None = None
    jobs_fetched: int | None = None
    jobs_filtered: int | None = None
    jobs_new: int | None = None
    jobs_scored: int | None = None
    jobs_notified: int | None = None
    errors: list[StageError] = Field(default_factory=list)
    duration_seconds: float | None = None
