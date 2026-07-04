"""Supabase writes: upsert-on-guid-conflict, run-row insert/finalize, error sanitizer.

Two idempotency guarantees live here (SPEC.md Decisions 2, 14):
- Inserts are upsert(on_conflict="guid", ignore_duplicates=True) so the unique
  constraint is a backstop, not a crash source; jobs_new counts rows actually
  inserted (PostgREST returns only inserted rows under ignore-duplicates).
- Scoring updates are per-row so a mid-run crash loses at most one job's work.

PostgREST takes literal JSON values only — no server-side now() or column
increments — so every timestamp is client-generated UTC ISO and score_attempts
is read-modify-write (safe: the Actions concurrency group forbids parallel writers).

workflow_runs.errors is world-readable via anon SELECT, so every persisted
message is sanitized: URLs stripped (the Slack webhook URL IS the credential,
Decision 19), only the exception type name kept, length capped.
"""

import logging
import re
from datetime import datetime, timezone

from pulseflow.models import Job, JobStatus, ScoreResult, StageError, WorkflowRun

logger = logging.getLogger(__name__)

_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
_MAX_MESSAGE_LEN = 500
_LIFETIME_ATTEMPTS_CAP = 6  # 3 runs' worth; row excluded from candidates past this


def sanitize_message(message: str) -> str:
    """Strip URLs and cap length before a message can reach a world-readable row."""
    return _URL_RE.sub("[url]", message)[:_MAX_MESSAGE_LEN]


def make_stage_error(stage: str, exc: Exception) -> StageError:
    """Never store tracebacks — only the type name and a sanitized message."""
    return StageError(stage=stage, type=type(exc).__name__, message=sanitize_message(str(exc)))


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Store:
    """Thin wrapper over a supabase client. Injected everywhere for testability."""

    def __init__(self, client):
        self._client = client

    # --- jobs ---------------------------------------------------------------

    def insert_new_jobs(self, jobs: list[Job]) -> int:
        """Upsert with ignore-duplicates. Returns the count of rows ACTUALLY inserted."""
        if not jobs:
            return 0
        now_iso = _now().isoformat()
        rows = [
            {
                "guid": j.guid,
                "source": j.source,
                "url": j.url,
                "title": j.title,
                "description": j.description,
                "status": JobStatus.NEW.value,
                "score_attempts": 0,
                "fetched_at": (j.fetched_at or _now()).isoformat() if j.fetched_at else now_iso,
            }
            for j in jobs
        ]
        res = (
            self._client.table("jobs")
            .upsert(rows, on_conflict="guid", ignore_duplicates=True, returning="representation")
            .execute()
        )
        return len(res.data or [])

    def fetch_scoring_candidates(self, cap: int) -> list[dict]:
        """One query covers this run's inserts AND leftovers from prior degraded runs.
        Ordered newest-first (a fresh job's notification is worth more) with an id
        tiebreak for deterministic LIMIT (Decision 14)."""
        res = (
            self._client.table("jobs")
            .select("id, guid, title, description, fetched_at, score_attempts")
            .eq("status", JobStatus.NEW.value)
            .lt("score_attempts", _LIFETIME_ATTEMPTS_CAP)
            .order("fetched_at", desc=True)
            .order("id")
            .limit(cap)
            .execute()
        )
        return res.data or []

    def mark_scored(self, job_id: str, result: ScoreResult) -> None:
        """Single UPDATE to SCORED (Decision 14). Raises on DB failure — caught by the caller."""
        self._client.table("jobs").update(
            {
                "status": JobStatus.SCORED.value,
                "score": result.score,
                "reasoning": result.reasoning,
                "scored_at": _now().isoformat(),
            }
        ).eq("id", job_id).execute()

    def bump_score_attempts(self, job_id: str, current_attempts: int, made: int) -> None:
        """Read-modify-write the lifetime counter after a degraded scoring attempt."""
        self._client.table("jobs").update(
            {"score_attempts": current_attempts + made}
        ).eq("id", job_id).execute()

    # --- workflow_runs ------------------------------------------------------

    def start_run(self) -> tuple[str | None, datetime]:
        """Insert the run row up front (started_at only) so early crashes still leave a trail.
        Returns (run_id or None, started_at)."""
        started_at = _now()
        try:
            res = (
                self._client.table("workflow_runs")
                .insert({"started_at": started_at.isoformat()})
                .execute()
            )
            return res.data[0]["id"], started_at
        except Exception as exc:  # noqa: BLE001 — run row must never crash the pipeline
            logger.error("run row insert failed", extra={"kind": type(exc).__name__})
            return None, started_at

    def finalize_run(self, run: WorkflowRun) -> bool:
        """Best-effort finalize. Swallows its own failures (Actions stdout is the
        fallback trail); never influences the exit code."""
        if run.id is None:
            return False
        finished = _now()
        payload = {
            "finished_at": finished.isoformat(),
            "jobs_fetched": run.jobs_fetched,
            "jobs_filtered": run.jobs_filtered,
            "jobs_new": run.jobs_new,
            "jobs_scored": run.jobs_scored,
            "jobs_notified": run.jobs_notified,
            "errors": [e.model_dump() for e in run.errors],
            "duration_seconds": (finished - run.started_at).total_seconds(),
        }
        try:
            self._client.table("workflow_runs").update(payload).eq("id", run.id).execute()
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("run finalize failed", extra={"kind": type(exc).__name__})
            return False
