"""Configuration: keywords.json via Pydantic + env fail-fast.

Never logs environment VALUES (SPEC.md Decision 19). Env loading lands at Phase 1.
"""

from pathlib import Path

from pydantic import BaseModel, Field, HttpUrl

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "keywords.json"


class KeywordsConfig(BaseModel):
    """Shape of config/keywords.json — the editable-without-code surface."""

    feed_urls: list[HttpUrl] = Field(min_length=1)
    keywords: list[str] = Field(min_length=1)
    min_score: int = Field(ge=1, le=10)
    heartbeat: bool
    max_jobs_scored_per_run: int = Field(ge=1)


def load_keywords_config(path: Path = CONFIG_PATH) -> KeywordsConfig:
    return KeywordsConfig.model_validate_json(path.read_text())
