"""Parses the REAL config/keywords.json through the Pydantic model (SPEC.md Decision 9):
a malformed config edit can never reach the cron."""

import pytest
from pydantic import ValidationError

from pulseflow.config import (
    CONFIG_PATH,
    DEFAULT_MODEL,
    KeywordsConfig,
    MissingEnvError,
    load_env_config,
    load_keywords_config,
)


def test_real_keywords_json_parses():
    cfg = load_keywords_config()
    assert CONFIG_PATH.name == "keywords.json"
    assert len(cfg.feed_urls) >= 1
    assert all(str(u).startswith("https://www.freelancer.com/rss.xml") for u in cfg.feed_urls)
    assert len(cfg.keywords) >= 1
    assert all(isinstance(k, str) and k for k in cfg.keywords)
    assert 1 <= cfg.min_score <= 10
    assert isinstance(cfg.heartbeat, bool)
    assert cfg.max_jobs_scored_per_run >= 1


def test_min_score_out_of_bounds_rejected():
    raw = load_keywords_config().model_dump(mode="json")
    raw["min_score"] = 11
    with pytest.raises(ValidationError):
        KeywordsConfig.model_validate(raw)


def test_empty_feed_urls_rejected():
    raw = load_keywords_config().model_dump(mode="json")
    raw["feed_urls"] = []
    with pytest.raises(ValidationError):
        KeywordsConfig.model_validate(raw)


FULL_ENV = {
    "ANTHROPIC_API_KEY": "sk-test-anthropic",
    "SUPABASE_URL": "https://x.supabase.co",
    "SUPABASE_SECRET_KEY": "sb_secret_test",
    "SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/T/B/x",
}


def test_dry_run_needs_only_anthropic_key():
    cfg = load_env_config(dry_run=True, environ={"ANTHROPIC_API_KEY": "sk-test"})
    assert cfg.anthropic_api_key == "sk-test"
    assert cfg.supabase_url is None
    assert cfg.model == DEFAULT_MODEL


def test_full_run_requires_all_four_and_names_missing_only():
    env = {k: v for k, v in FULL_ENV.items() if k != "SLACK_WEBHOOK_URL"}
    env["SUPABASE_SECRET_KEY"] = ""  # empty counts as missing
    with pytest.raises(MissingEnvError) as exc:
        load_env_config(dry_run=False, environ=env)
    assert exc.value.missing == ["SUPABASE_SECRET_KEY", "SLACK_WEBHOOK_URL"]
    # names only — no VALUE from the environment appears in the message
    assert "sk-test-anthropic" not in str(exc.value)


def test_full_run_loads_and_model_overridable():
    cfg = load_env_config(dry_run=False, environ={**FULL_ENV, "PULSEFLOW_MODEL": "test-model"})
    assert cfg.model == "test-model"
    assert cfg.slack_webhook_url == FULL_ENV["SLACK_WEBHOOK_URL"]


def test_env_config_repr_never_leaks_values():
    cfg = load_env_config(dry_run=False, environ=FULL_ENV)
    shown = f"{cfg!r} {cfg}"
    for value in FULL_ENV.values():
        assert value not in shown
