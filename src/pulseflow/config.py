"""Configuration: keywords.json via Pydantic + env fail-fast.

Never logs or embeds environment VALUES anywhere (SPEC.md Decision 19) —
errors name the missing variables only.
"""

import os
from collections.abc import Mapping
from pathlib import Path

from pydantic import BaseModel, Field, HttpUrl

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "keywords.json"

DEFAULT_MODEL = "claude-haiku-4-5"
MODEL_ENV_VAR = "PULSEFLOW_MODEL"

DRY_RUN_ENV_VARS: tuple[str, ...] = ("ANTHROPIC_API_KEY",)
FULL_RUN_ENV_VARS: tuple[str, ...] = (
    "ANTHROPIC_API_KEY",
    "SUPABASE_URL",
    "SUPABASE_SECRET_KEY",
    "SLACK_WEBHOOK_URL",
)


class MissingEnvError(RuntimeError):
    """Raised when required environment variables are absent. Carries names only."""

    def __init__(self, missing: list[str]):
        self.missing = missing
        super().__init__(f"missing required environment variables: {', '.join(missing)}")


class EnvConfig(BaseModel):
    anthropic_api_key: str
    supabase_url: str | None = None
    supabase_secret_key: str | None = None
    slack_webhook_url: str | None = None
    model: str = DEFAULT_MODEL

    def __repr__(self) -> str:  # defense in depth: never leak values via repr
        return f"EnvConfig(model={self.model!r}, secrets=<redacted>)"

    __str__ = __repr__


def load_env_config(
    *, dry_run: bool, environ: Mapping[str, str] = os.environ
) -> EnvConfig:
    """Fail fast when a mode's required variables are absent or empty."""
    required = DRY_RUN_ENV_VARS if dry_run else FULL_RUN_ENV_VARS
    missing = [name for name in required if not environ.get(name)]
    if missing:
        raise MissingEnvError(missing)
    return EnvConfig(
        anthropic_api_key=environ["ANTHROPIC_API_KEY"],
        supabase_url=environ.get("SUPABASE_URL"),
        supabase_secret_key=environ.get("SUPABASE_SECRET_KEY"),
        slack_webhook_url=environ.get("SLACK_WEBHOOK_URL"),
        model=environ.get(MODEL_ENV_VAR) or DEFAULT_MODEL,
    )


class KeywordsConfig(BaseModel):
    """Shape of config/keywords.json — the editable-without-code surface."""

    feed_urls: list[HttpUrl] = Field(min_length=1)
    keywords: list[str] = Field(min_length=1)
    min_score: int = Field(ge=1, le=10)
    heartbeat: bool
    max_jobs_scored_per_run: int = Field(ge=1)


def load_keywords_config(path: Path = CONFIG_PATH) -> KeywordsConfig:
    return KeywordsConfig.model_validate_json(path.read_text())
