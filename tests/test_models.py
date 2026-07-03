from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from pulseflow.models import Job, JobStatus, ScoreResult, StageError, WorkflowRun

NOW = datetime(2026, 7, 4, 8, 17, tzinfo=timezone.utc)


def test_job_defaults():
    job = Job(guid="Freelancer_project_123", fetched_at=NOW)
    assert job.status is JobStatus.NEW
    assert job.source == "freelancer"
    assert job.score is None
    assert job.score_attempts == 0
    assert job.description == ""


def test_job_guid_required_and_non_empty():
    with pytest.raises(ValidationError):
        Job(fetched_at=NOW)  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        Job(guid="", fetched_at=NOW)


@pytest.mark.parametrize("bad_score", [0, 11, -1])
def test_job_score_bounds(bad_score):
    with pytest.raises(ValidationError):
        Job(guid="g", fetched_at=NOW, score=bad_score)


def test_job_status_enum_only():
    with pytest.raises(ValidationError):
        Job(guid="g", fetched_at=NOW, status="GAVE_UP")
    assert {s.value for s in JobStatus} == {"NEW", "SCORED", "NOTIFIED"}


@pytest.mark.parametrize("bad_score", [0, 11])
def test_score_result_bounds(bad_score):
    with pytest.raises(ValidationError):
        ScoreResult(score=bad_score, reasoning="r")


def test_score_result_requires_reasoning():
    with pytest.raises(ValidationError):
        ScoreResult(score=7)  # type: ignore[call-arg]


def test_workflow_run_errors_shape():
    run = WorkflowRun(
        started_at=NOW,
        errors=[StageError(stage="fetch", type="HTTPStatusError", message="feed returned 500")],
    )
    dumped = run.model_dump(mode="json")
    assert dumped["errors"] == [
        {"stage": "fetch", "type": "HTTPStatusError", "message": "feed returned 500"}
    ]
    assert run.finished_at is None and run.jobs_fetched is None
