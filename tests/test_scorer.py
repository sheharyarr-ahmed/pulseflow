"""Mocked-client scorer tests: success, retry-then-success, double-failure -> degradation."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import anthropic
import httpx
from pydantic import ValidationError

from pulseflow.models import Job, ScoreResult
from pulseflow.scorer import DESCRIPTION_TRUNCATE, ScoreOutcome, load_scoring_prompt, score_job

NOW = datetime(2026, 7, 4, tzinfo=timezone.utc)
JOB = Job(guid="Freelancer_project_1", title="Next.js MVP", description="x" * 3000, fetched_at=NOW)
PROMPT = "score it"


def ok_response(score: int = 8) -> SimpleNamespace:
    return SimpleNamespace(
        parsed_output=ScoreResult(score=score, reasoning="direct stack match"),
        stop_reason="end_turn",
    )


def validation_error() -> ValidationError:
    return ValidationError.from_exception_data("ScoreResult", [])


def api_error() -> anthropic.APIConnectionError:
    return anthropic.APIConnectionError(request=httpx.Request("POST", "https://api.anthropic.com"))


def make_client(*outcomes) -> Mock:
    client = Mock()
    client.messages.parse.side_effect = list(outcomes)
    return client


def test_success_first_attempt():
    client = make_client(ok_response())
    outcome = score_job(client, JOB, PROMPT, model="claude-haiku-4-5")
    assert outcome.result is not None and outcome.result.score == 8
    assert outcome.attempts == 1 and outcome.error is None


def test_retry_then_success():
    client = make_client(api_error(), ok_response(7))
    outcome = score_job(client, JOB, PROMPT, model="claude-haiku-4-5")
    assert outcome.result is not None and outcome.result.score == 7
    assert outcome.attempts == 2


def test_double_failure_degrades_never_raises():
    client = make_client(validation_error(), api_error())
    outcome = score_job(client, JOB, PROMPT, model="claude-haiku-4-5")
    assert outcome == ScoreOutcome(result=None, attempts=2, error=outcome.error)
    assert outcome.error is not None and outcome.error.stage == "score"
    assert client.messages.parse.call_count == 2


def test_max_tokens_stop_counts_as_failed_attempt():
    truncated = SimpleNamespace(parsed_output=None, stop_reason="max_tokens")
    client = make_client(truncated, ok_response(9))
    outcome = score_job(client, JOB, PROMPT, model="claude-haiku-4-5")
    assert outcome.result is not None and outcome.attempts == 2


def test_refusal_counts_as_failed_attempt():
    refusal = SimpleNamespace(parsed_output=None, stop_reason="refusal")
    client = make_client(refusal, refusal)
    outcome = score_job(client, JOB, PROMPT, model="claude-haiku-4-5")
    assert outcome.result is None and outcome.error.type == "stop_refusal"


def test_description_truncated_in_request_full_text_untouched():
    client = make_client(ok_response())
    score_job(client, JOB, PROMPT, model="claude-haiku-4-5")
    sent = client.messages.parse.call_args.kwargs["messages"][0]["content"]
    assert len(sent) < DESCRIPTION_TRUNCATE + 100
    assert len(JOB.description) == 3000  # persisted object untouched


def test_prompt_file_loads_and_carries_neutrality_line():
    prompt = load_scoring_prompt()
    assert "displayed publicly" in prompt and "9–10" in prompt
