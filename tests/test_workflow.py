"""Full pipeline with all externals mocked (SPEC.md test_workflow.py).

Focus: the orchestration invariants — persist-then-score ordering, per-row
scoring, degraded-run recovery, and the end-computed exit code (fetch/Supabase
fail red; LLM degradation stays green; a single dead feed among several does not
fail the run, all feeds dead does)."""

from datetime import datetime, timezone

import pytest

from pulseflow.config import KeywordsConfig
from pulseflow.models import Job, ScoreResult, StageError
from pulseflow.scorer import ScoreOutcome
from pulseflow.workflow import run_pipeline

NOW = datetime(2026, 7, 4, tzinfo=timezone.utc)


def cfg(max_jobs=50):
    return KeywordsConfig(
        feed_urls=["https://www.freelancer.com/rss.xml?keyword=react"],
        keywords=["Next.js", "AI agent"],
        min_score=7,
        heartbeat=True,
        max_jobs_scored_per_run=max_jobs,
    )


def job(guid, title="Next.js MVP", description="build it"):
    return Job(guid=guid, title=title, description=description, fetched_at=NOW)


class FakeSource:
    def __init__(self, jobs, errors=()):
        self._jobs, self._errors = jobs, list(errors)

    def fetch(self):
        return list(self._jobs), list(self._errors)


class FakeStore:
    """In-memory stand-in exposing the Store surface run_pipeline uses."""

    def __init__(self, candidates=None, fail_on=None):
        self.rows = candidates or []
        self.fail_on = fail_on or set()
        self.inserted = []
        self.scored = []          # (id, ScoreResult)
        self.bumped = []          # (id, current, made)
        self.finalized = None

    def start_run(self):
        return "run-1", NOW

    def insert_new_jobs(self, jobs):
        if "persist" in self.fail_on:
            raise RuntimeError("supabase insert down")
        self.inserted = list(jobs)
        return len(jobs)

    def fetch_scoring_candidates(self, cap):
        if "query" in self.fail_on:
            raise RuntimeError("supabase select down")
        return self.rows[:cap]

    def mark_scored(self, job_id, result):
        if "update" in self.fail_on:
            raise RuntimeError("supabase update down")
        self.scored.append((job_id, result))

    def bump_score_attempts(self, job_id, current, made):
        self.bumped.append((job_id, current, made))

    def finalize_run(self, run):
        self.finalized = run
        return True


def identity_dedupe(jobs):
    return jobs


def scorer_returning(score_val=8):
    return lambda j: ScoreOutcome(result=ScoreResult(score=score_val, reasoning="fit"), attempts=1)


def degraded_scorer():
    return lambda j: ScoreOutcome(
        result=None, attempts=2, error=StageError(stage="score", type="stop_refusal", message="x")
    )


def test_happy_path_counts_and_green_exit():
    store = FakeStore(candidates=[{"id": "id-1", "guid": "g1", "title": "t", "description": "d", "fetched_at": NOW.isoformat(), "score_attempts": 0}])
    result = run_pipeline(
        config=cfg(),
        source=FakeSource([job("g1"), job("g2", title="wordpress theme")]),
        store=store,
        dedupe=identity_dedupe,
        score=scorer_returning(9),
        feed_count=1,
    )
    assert result.jobs_fetched == 2
    assert result.jobs_filtered == 1          # only the Next.js job matched
    assert result.jobs_new == 1               # inserted the one fresh match
    assert result.jobs_scored == 1
    assert store.scored == [("id-1", ScoreResult(score=9, reasoning="fit"))]
    assert result.exit_code == 0
    assert store.finalized is not None


def test_llm_degradation_bumps_attempts_and_stays_green():
    store = FakeStore(candidates=[{"id": "id-1", "guid": "g1", "title": "t", "description": "d", "fetched_at": NOW.isoformat(), "score_attempts": 2}])
    result = run_pipeline(
        config=cfg(),
        source=FakeSource([job("g1")]),
        store=store,
        dedupe=identity_dedupe,
        score=degraded_scorer(),
        feed_count=1,
    )
    assert result.jobs_scored == 0
    assert store.bumped == [("id-1", 2, 2)]   # current 2 + 2 attempts made -> 4
    assert store.scored == []
    assert result.exit_code == 0              # LLM failure degrades, not red
    assert any(e.stage == "score" for e in result.errors)


def test_all_feeds_dead_exits_red():
    errs = [StageError(stage="fetch", type="feed_empty", message="0 entries")]
    result = run_pipeline(
        config=cfg(),
        source=FakeSource([], errors=errs),
        store=FakeStore(),
        dedupe=identity_dedupe,
        score=scorer_returning(),
        feed_count=1,               # 1 error == 1 feed == all dead
    )
    assert result.exit_code == 1


def test_single_broken_feed_among_several_stays_green():
    errs = [StageError(stage="fetch", type="feed_content_type", message="html")]
    result = run_pipeline(
        config=cfg(),
        source=FakeSource([job("g1")], errors=errs),
        store=FakeStore(candidates=[]),
        dedupe=identity_dedupe,
        score=scorer_returning(),
        feed_count=4,               # 1 error out of 4 feeds -> not all dead
    )
    assert any(e.stage == "fetch" for e in result.errors)   # still recorded
    assert result.exit_code == 0                            # but not red


def test_supabase_persist_failure_exits_red_but_continues():
    store = FakeStore(candidates=[], fail_on={"persist"})
    result = run_pipeline(
        config=cfg(),
        source=FakeSource([job("g1")]),
        store=store,
        dedupe=identity_dedupe,
        score=scorer_returning(),
        feed_count=1,
    )
    assert any(e.stage == "persist" for e in result.errors)
    assert result.exit_code == 1
    assert store.finalized is not None       # still finalized despite the failure


def test_score_update_db_failure_is_infra():
    store = FakeStore(
        candidates=[{"id": "id-1", "guid": "g1", "title": "t", "description": "d", "fetched_at": NOW.isoformat(), "score_attempts": 0}],
        fail_on={"update"},
    )
    result = run_pipeline(
        config=cfg(),
        source=FakeSource([job("g1")]),
        store=store,
        dedupe=identity_dedupe,
        score=scorer_returning(),
        feed_count=1,
    )
    assert any(e.stage == "score_update" for e in result.errors)
    assert result.exit_code == 1


def test_notify_receives_run_counts():
    store = FakeStore(candidates=[])
    seen = {}

    def fake_notify(s, counts):
        seen.update(counts)
        return 2

    result = run_pipeline(
        config=cfg(),
        source=FakeSource([job("g1"), job("g2", title="wordpress")]),
        store=store,
        dedupe=identity_dedupe,
        score=scorer_returning(),
        notify=fake_notify,
        feed_count=1,
    )
    assert result.jobs_notified == 2
    assert seen == {"fetched": 2, "matched": 1, "new": 1, "scored": 0}  # scored 0: no NEW candidates


def test_slack_post_failure_degrades_stays_green():
    from pulseflow.notifier import SlackPostError

    def slack_down(s, counts):
        raise SlackPostError("slack webhook failed status=500 https://hooks.slack.com/secret")

    result = run_pipeline(
        config=cfg(),
        source=FakeSource([]),
        store=FakeStore(candidates=[]),
        dedupe=identity_dedupe,
        score=scorer_returning(),
        notify=slack_down,
        feed_count=1,
    )
    assert any(e.stage == "notify" for e in result.errors)
    assert result.exit_code == 0  # Slack outage self-heals; not red
    assert all("hooks.slack.com" not in e.message for e in result.errors)  # sanitized


def test_supabase_failure_in_notify_path_exits_red():
    # A Supabase pool SELECT / CAS flip failure raises a non-Slack error -> infra.
    def db_down(s, counts):
        raise RuntimeError("postgrest connection reset")

    result = run_pipeline(
        config=cfg(),
        source=FakeSource([]),
        store=FakeStore(candidates=[]),
        dedupe=identity_dedupe,
        score=scorer_returning(),
        notify=db_down,
        feed_count=1,
    )
    assert any(e.stage == "notify_db" for e in result.errors)
    assert result.exit_code == 1  # broken DB plumbing must show red (Decision 7)


def test_cap_limits_candidates_scored():
    rows = [{"id": f"id-{i}", "guid": f"g{i}", "title": "t", "description": "d", "fetched_at": NOW.isoformat(), "score_attempts": 0} for i in range(5)]
    store = FakeStore(candidates=rows)
    result = run_pipeline(
        config=cfg(max_jobs=3),
        source=FakeSource([]),
        store=store,
        dedupe=identity_dedupe,
        score=scorer_returning(),
        feed_count=1,
    )
    assert result.jobs_scored == 3
