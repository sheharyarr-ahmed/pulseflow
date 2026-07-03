"""Parses the REAL config/keywords.json through the Pydantic model (SPEC.md Decision 9):
a malformed config edit can never reach the cron."""

import pytest
from pydantic import ValidationError

from pulseflow.config import CONFIG_PATH, KeywordsConfig, load_keywords_config


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
