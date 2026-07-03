"""Job scoring via Anthropic structured output (messages.parse -> ScoreResult).

Client-side Pydantic validation is the real gate: a ValidationError, refusal,
missing parsed output, or max_tokens stop counts as a failed attempt
(SPEC.md Decision 6). Per-run retry cap: 2 attempts. LLM failure degrades —
it never raises out of score_job (Decision 7); the DB-level lifetime cap of
6 attempts lives in the orchestrator (Phase 2).
"""

import logging
from dataclasses import dataclass
from pathlib import Path

import anthropic
from pydantic import ValidationError

from pulseflow.models import Job, ScoreResult, StageError

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent / "prompts" / "scoring.md"
MAX_ATTEMPTS = 2
MAX_TOKENS = 256
DESCRIPTION_TRUNCATE = 2_000  # full text still persisted (Decision 17)

_FAILED_STOP_REASONS = ("max_tokens", "refusal")


@dataclass
class ScoreOutcome:
    """Per-job scoring outcome: a result or a degradation, plus attempts made."""

    result: ScoreResult | None
    attempts: int
    error: StageError | None = None


def load_scoring_prompt(path: Path = PROMPT_PATH) -> str:
    return path.read_text()


def _job_message(job: Job) -> str:
    return (
        f"Title: {job.title}\n\n"
        f"Description: {job.description[:DESCRIPTION_TRUNCATE]}"
    )


def score_job(
    client: anthropic.Anthropic,
    job: Job,
    prompt: str,
    model: str,
    max_attempts: int = MAX_ATTEMPTS,
) -> ScoreOutcome:
    last_error: StageError | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            response = client.messages.parse(
                model=model,
                max_tokens=MAX_TOKENS,
                system=prompt,
                messages=[{"role": "user", "content": _job_message(job)}],
                output_format=ScoreResult,
            )
        except (ValidationError, anthropic.APIError) as exc:
            last_error = StageError(stage="score", type=type(exc).__name__, message=str(exc))
            logger.warning(
                "score attempt failed",
                extra={"guid": job.guid, "attempt": attempt, "kind": type(exc).__name__},
            )
            continue

        stop_reason = getattr(response, "stop_reason", None)
        parsed = getattr(response, "parsed_output", None)
        if stop_reason in _FAILED_STOP_REASONS or parsed is None:
            kind = f"stop_{stop_reason}" if stop_reason in _FAILED_STOP_REASONS else "no_parsed_output"
            last_error = StageError(stage="score", type=kind, message=f"guid={job.guid}")
            logger.warning(
                "score attempt unusable",
                extra={"guid": job.guid, "attempt": attempt, "kind": kind},
            )
            continue

        return ScoreOutcome(result=parsed, attempts=attempt)

    return ScoreOutcome(result=None, attempts=max_attempts, error=last_error)
