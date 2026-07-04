"""PulseFlow entry point — invoked by the daily cron and by hand.

Usage:
    uv run python scripts/run_hunt.py            # full pipeline (Phase 2+)
    uv run python scripts/run_hunt.py --dry-run  # fetch/filter/score only, no DB/Slack

Dry-run touches no Supabase and no Slack: fetch -> filter -> in-memory GUID
dedupe -> score up to the per-run cap -> print. Requires only ANTHROPIC_API_KEY.
"""

import argparse
import logging
import sys

import anthropic
from dotenv import load_dotenv

from pulseflow.config import (
    FULL_RUN_ENV_VARS,
    MissingEnvError,
    load_env_config,
    load_keywords_config,
)
from pulseflow.dedupe import remove_seen
from pulseflow.fetcher import FreelancerRSS
from pulseflow.filters import filter_jobs
from pulseflow.logging_setup import setup_logging
from pulseflow.notifier import notify as slack_notify
from pulseflow.scorer import load_scoring_prompt, score_job
from pulseflow.store import Store
from pulseflow.workflow import run_pipeline

logger = logging.getLogger("pulseflow.run_hunt")


def run_dry() -> int:
    keywords_cfg = load_keywords_config()
    env = load_env_config(dry_run=True)

    source = FreelancerRSS([str(u) for u in keywords_cfg.feed_urls])
    jobs, fetch_errors = source.fetch()
    matched = filter_jobs(jobs, keywords_cfg.keywords)
    candidates = matched[: keywords_cfg.max_jobs_scored_per_run]
    logger.info(
        "dry-run pipeline",
        extra={
            "fetched": len(jobs),
            "feed_errors": len(fetch_errors),
            "matched": len(matched),
            "to_score": len(candidates),
        },
    )

    client = anthropic.Anthropic(api_key=env.anthropic_api_key)
    prompt = load_scoring_prompt()
    print(f"\n{'score':>5}  {'attempts':>8}  title / reasoning")
    print("-" * 100)
    for job in candidates:
        outcome = score_job(client, job, prompt, model=env.model)
        if outcome.result is None:
            kind = outcome.error.type if outcome.error else "unknown"
            print(f"{'—':>5}  {outcome.attempts:>8}  {job.title}  [degraded: {kind}]")
        else:
            print(f"{outcome.result.score:>5}  {outcome.attempts:>8}  {job.title}")
            print(f"{'':>5}  {'':>8}  ↳ {outcome.result.reasoning}")
    print("-" * 100)
    print(f"fetched={len(jobs)} matched={len(matched)} scored={len(candidates)} (dry-run: nothing persisted)")
    return 0


def run_full() -> int:
    from supabase import create_client

    keywords_cfg = load_keywords_config()
    env = load_env_config(dry_run=False, required=FULL_RUN_ENV_VARS)

    client = create_client(env.supabase_url, env.supabase_secret_key)
    store = Store(client)
    source = FreelancerRSS([str(u) for u in keywords_cfg.feed_urls])
    anthropic_client = anthropic.Anthropic(api_key=env.anthropic_api_key, timeout=60.0)
    prompt = load_scoring_prompt()

    result = run_pipeline(
        config=keywords_cfg,
        source=source,
        store=store,
        dedupe=lambda jobs: remove_seen(client, jobs),
        score=lambda job: score_job(anthropic_client, job, prompt, model=env.model),
        notify=lambda s, counts: slack_notify(
            s,
            counts,
            webhook_url=env.slack_webhook_url,
            min_score=keywords_cfg.min_score,
            heartbeat=keywords_cfg.heartbeat,
        ),
        feed_count=len(keywords_cfg.feed_urls),
    )
    print(
        f"fetched={result.jobs_fetched} matched={result.jobs_filtered} "
        f"new={result.jobs_new} scored={result.jobs_scored} "
        f"errors={len(result.errors)} exit={result.exit_code}"
    )
    return result.exit_code


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the PulseFlow job hunt pipeline.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="fetch, filter, and score without touching Supabase or Slack",
    )
    args = parser.parse_args()

    load_dotenv()
    setup_logging()
    try:
        return run_dry() if args.dry_run else run_full()
    except MissingEnvError as exc:
        print(f"pulseflow: {exc}", file=sys.stderr)  # names only, never values
        return 1


if __name__ == "__main__":
    sys.exit(main())
