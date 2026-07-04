"""Orchestrator: fetch -> filter -> dedupe -> persist NEW -> score -> notify.

Pipeline order is persist-then-score (SPEC.md Decision 14): rows are born NEW
right after dedupe, the scorer works off a DB query, and each success is a
per-row UPDATE — so "data capture never depends on the LLM" is literally true
and a degraded run's recovery path is the same code as a normal run.

Exit code is computed at the END from accumulated errors, never raised mid-run
(Decision 7 + resolution to the Decision 7/18 contradiction): the pipeline
always reaches notify (so a dead feed still shows a heartbeat) and finalize.
Fetch failure (ALL feeds dead) or ANY Supabase failure -> exit 1. LLM failure
alone degrades -> exit 0, next run's candidate query retries the row.

Collaborators are injected so the whole pipeline is testable with no network.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone

from pulseflow.config import KeywordsConfig
from pulseflow.filters import filter_jobs
from pulseflow.models import Job, StageError, WorkflowRun
from pulseflow.notifier import SlackPostError
from pulseflow.scorer import ScoreOutcome
from pulseflow.store import Store, make_stage_error

logger = logging.getLogger(__name__)

# Supabase stages whose failure must show a red run (Decision 7). Scoring is
# excluded (LLM failure degrades) and finalize is excluded (best-effort). Fetch
# is handled separately: a single broken feed continues, only ALL feeds dead
# exits red (Decision 18) — so a fetch StageError alone does NOT fail the run.
# "notify_db" covers the Supabase read/write inside the notify path (pool SELECT,
# CAS flip); a pure Slack-post failure is stage "notify" and stays green.
_INFRA_STAGES = frozenset({"persist", "score_query", "score_update", "notify_db"})


@dataclass
class RunResult:
    jobs_fetched: int = 0
    jobs_filtered: int = 0
    jobs_new: int = 0
    jobs_scored: int = 0
    jobs_notified: int = 0
    errors: list[StageError] = field(default_factory=list)
    exit_code: int = 0


def _job_from_row(row: dict) -> Job:
    raw = row.get("fetched_at")
    fetched_at = datetime.fromisoformat(raw) if raw else datetime.now(timezone.utc)
    return Job(
        guid=row["guid"],
        title=row.get("title"),
        description=row.get("description") or "",
        fetched_at=fetched_at,
    )


def run_pipeline(
    *,
    config: KeywordsConfig,
    source,
    store: Store,
    dedupe: Callable[[list[Job]], list[Job]],
    score: Callable[[Job], ScoreOutcome],
    notify: Callable[[Store, dict], int] | None = None,
    feed_count: int,
) -> RunResult:
    result = RunResult()
    run_id, started_at = store.start_run()

    # --- fetch --------------------------------------------------------------
    jobs, fetch_errors = source.fetch()
    result.jobs_fetched = len(jobs)
    result.errors.extend(fetch_errors)
    all_feeds_dead = bool(fetch_errors) and len(fetch_errors) >= feed_count
    if all_feeds_dead:
        logger.error("all feeds failed", extra={"feeds": feed_count})  # exit 1 at the end

    # --- filter -------------------------------------------------------------
    matched = filter_jobs(jobs, config.keywords)
    result.jobs_filtered = len(matched)

    # --- dedupe + persist NEW ----------------------------------------------
    try:
        fresh = dedupe(matched)
        result.jobs_new = store.insert_new_jobs(fresh)
    except Exception as exc:  # noqa: BLE001
        result.errors.append(make_stage_error("persist", exc))
        logger.error("persist stage failed", extra={"kind": type(exc).__name__})

    # --- score candidates (this run's inserts + prior degraded leftovers) ---
    try:
        candidates = store.fetch_scoring_candidates(config.max_jobs_scored_per_run)
    except Exception as exc:  # noqa: BLE001
        candidates = []
        result.errors.append(make_stage_error("score_query", exc))
        logger.error("candidate query failed", extra={"kind": type(exc).__name__})

    for row in candidates:
        outcome = score(_job_from_row(row))
        try:
            if outcome.result is not None:
                store.mark_scored(row["id"], outcome.result)
                result.jobs_scored += 1
            else:
                store.bump_score_attempts(row["id"], row.get("score_attempts", 0), outcome.attempts)
                if outcome.error is not None:
                    result.errors.append(outcome.error)  # LLM degradation, not infra
        except Exception as exc:  # noqa: BLE001 — DB write failure IS infra
            result.errors.append(make_stage_error("score_update", exc))
            logger.error("score update failed", extra={"kind": type(exc).__name__})

    # --- notify (Phase 3 wires the real Slack notifier; heartbeat on quiet days) ---
    if notify is not None:
        counts = {
            "fetched": result.jobs_fetched,
            "matched": result.jobs_filtered,
            "new": result.jobs_new,
            "scored": result.jobs_scored,
        }
        try:
            result.jobs_notified = notify(store, counts)
        except SlackPostError as exc:
            # Slack outage self-heals: rows stay SCORED and re-post next run. Green.
            result.errors.append(make_stage_error("notify", exc))
            logger.error("slack post failed", extra={"kind": type(exc).__name__})
        except Exception as exc:  # noqa: BLE001 — Supabase pool SELECT / CAS flip failure
            # Broken DB plumbing in the notify path must show a red run (Decision 7).
            result.errors.append(make_stage_error("notify_db", exc))
            logger.error("notify db failure", extra={"kind": type(exc).__name__})

    # --- finalize + exit code ----------------------------------------------
    store.finalize_run(
        WorkflowRun(
            id=run_id,
            started_at=started_at,
            jobs_fetched=result.jobs_fetched,
            jobs_filtered=result.jobs_filtered,
            jobs_new=result.jobs_new,
            jobs_scored=result.jobs_scored,
            jobs_notified=result.jobs_notified,
            errors=result.errors,
        )
    )
    infra_failure = all_feeds_dead or any(e.stage in _INFRA_STAGES for e in result.errors)
    result.exit_code = 1 if infra_failure else 0
    logger.info(
        "run complete",
        extra={
            "fetched": result.jobs_fetched,
            "matched": result.jobs_filtered,
            "new": result.jobs_new,
            "scored": result.jobs_scored,
            "notified": result.jobs_notified,
            "errors": len(result.errors),
            "exit_code": result.exit_code,
        },
    )
    return result
