"""store.py: error sanitizer (no secrets in world-readable errors) + run-row logic.

The upsert ignore-duplicates / jobs_new-counting behavior is verified empirically
by the Phase 2 double-run gate, not here — postgrest semantics aren't unit-mockable
faithfully. These tests lock the sanitizer, the crash-safe run row, and call shapes.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock

from pulseflow.models import Job, ScoreResult, StageError, WorkflowRun
from pulseflow.store import Store, make_stage_error, sanitize_message

NOW = datetime(2026, 7, 4, tzinfo=timezone.utc)
WEBHOOK = "https://hooks.slack.com/services/T00/B00/XXXXsecretXXXX"


def test_sanitizer_strips_urls_including_http_and_https():
    msg = f"POST {WEBHOOK} failed; see http://internal/trace?token=abc"
    out = sanitize_message(msg)
    assert WEBHOOK not in out
    assert "http://internal" not in out
    assert out.count("[url]") == 2


def test_sanitizer_caps_length():
    assert len(sanitize_message("x" * 5000)) == 500


def test_stage_error_never_contains_webhook():
    exc = RuntimeError(f"connection to {WEBHOOK} refused")
    err = make_stage_error("notify", exc)
    serialized = str(err.model_dump())
    assert WEBHOOK not in serialized
    assert err.type == "RuntimeError"
    assert err.stage == "notify"


def test_serialized_errors_payload_hides_webhook():
    # Simulates what workflow_runs.errors would hold — the anon-readable row.
    errors = [make_stage_error("notify", RuntimeError(f"slack {WEBHOOK} 500"))]
    payload = [e.model_dump() for e in errors]
    assert WEBHOOK not in str(payload)


def _chain_mock(return_data):
    """A supabase-style fluent mock whose terminal .execute() returns .data."""
    client = MagicMock()
    execute = MagicMock()
    execute.execute.return_value = MagicMock(data=return_data)
    # every intermediate builder call returns the same object so chaining works
    client.table.return_value = execute
    for attr in ("insert", "upsert", "update", "select", "eq", "lt", "gte",
                 "order", "limit", "in_", "neq", "delete"):
        getattr(execute, attr).return_value = execute
    return client, execute


def test_start_run_returns_id():
    client, _ = _chain_mock([{"id": "run-123"}])
    run_id, started = Store(client).start_run()
    assert run_id == "run-123"
    assert started.tzinfo is not None


def test_start_run_swallows_failure_returns_none():
    client = MagicMock()
    client.table.side_effect = RuntimeError("db down")
    run_id, started = Store(client).start_run()
    assert run_id is None and started.tzinfo is not None


def test_finalize_run_noop_when_no_run_id():
    client = MagicMock()
    ok = Store(client).finalize_run(WorkflowRun(id=None, started_at=NOW))
    assert ok is False
    client.table.assert_not_called()


def test_finalize_run_swallows_failure():
    client = MagicMock()
    client.table.side_effect = RuntimeError("db down")
    ok = Store(client).finalize_run(WorkflowRun(id="run-1", started_at=NOW))
    assert ok is False  # never raises


def test_insert_new_jobs_counts_inserted_rows():
    client, execute = _chain_mock([{"guid": "a"}, {"guid": "b"}])
    jobs = [
        Job(guid="a", title="t", fetched_at=NOW),
        Job(guid="b", title="t", fetched_at=NOW),
        Job(guid="c", title="t", fetched_at=NOW),
    ]
    assert Store(client).insert_new_jobs(jobs) == 2  # only 2 rows returned == 2 inserted
    execute.upsert.assert_called_once()
    kwargs = execute.upsert.call_args.kwargs
    assert kwargs["on_conflict"] == "guid" and kwargs["ignore_duplicates"] is True


def test_insert_new_jobs_empty_short_circuits():
    client = MagicMock()
    assert Store(client).insert_new_jobs([]) == 0
    client.table.assert_not_called()


def test_mark_scored_and_bump_attempts_call_shapes():
    client, execute = _chain_mock([])
    store = Store(client)
    store.mark_scored("id-1", ScoreResult(score=9, reasoning="strong"))
    payload = execute.update.call_args.args[0]
    assert payload["status"] == "SCORED" and payload["score"] == 9 and "scored_at" in payload

    store.bump_score_attempts("id-2", current_attempts=2, made=2)
    assert execute.update.call_args.args[0] == {"score_attempts": 4}


def test_fetch_notification_pool_query_shape():
    client, execute = _chain_mock([{"id": "id-1"}])
    Store(client).fetch_notification_pool(min_score=7, top_n=3)
    execute.eq.assert_any_call("status", "SCORED")
    execute.gte.assert_any_call("score", 7)
    # a scored_at cutoff is applied (24h staleness) and results are limited to top_n
    assert any(c.args[0] == "scored_at" for c in execute.gte.call_args_list)
    execute.limit.assert_called_with(3)


def test_flip_to_notified_is_compare_and_swap():
    client, execute = _chain_mock([{"id": "id-1"}, {"id": "id-2"}])
    flipped = Store(client).flip_to_notified(["id-1", "id-2"])
    assert flipped == 2
    payload = execute.update.call_args.args[0]
    assert payload["status"] == "NOTIFIED" and "notified_at" in payload
    execute.eq.assert_any_call("status", "SCORED")  # the CAS guard
    execute.in_.assert_called_once_with("id", ["id-1", "id-2"])


def test_flip_to_notified_empty_is_noop():
    client = MagicMock()
    assert Store(client).flip_to_notified([]) == 0
    client.table.assert_not_called()
