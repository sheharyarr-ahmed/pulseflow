"""Slack notification: one message, top <=3, heartbeat, compare-and-swap status flip.

Semantics (SPEC.md Decision 15, P3): post ONE mrkdwn message with the top <=3
SCORED jobs above min_score from the last 24h, then flip exactly those rows with
a compare-and-swap. Post-then-flip is duplicate-over-drop: a crash between post
and flip may rarely re-post, but never silently loses a notification. On a quiet
run (0 qualifying), post a one-line heartbeat instead so silence always means
breakage. Titles are hostile input (Decision 20) — escaped for mrkdwn.
"""

import html as _html  # noqa: F401 — kept for intent; manual escaping below per Slack rules
import logging

import httpx

from pulseflow.store import Store

logger = logging.getLogger(__name__)

SLACK_TIMEOUT = httpx.Timeout(30)
TOP_N = 3
REASONING_TRUNCATE = 140


def escape_mrkdwn(text: str) -> str:
    """Slack requires &, <, > escaped in message text (link syntax uses < >)."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def truncate_reasoning(text: str | None, limit: int = REASONING_TRUNCATE) -> str:
    collapsed = " ".join((text or "").split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 1].rstrip() + "…"


def build_message(rows: list[dict]) -> str:
    lines = []
    for r in rows:
        title = escape_mrkdwn(r.get("title") or "(untitled)")
        url = r.get("url")
        link = f"<{url}|{title}>" if url else title
        lines.append(f"• {link} — *{r.get('score')}/10* — {truncate_reasoning(r.get('reasoning'))}")
    return "\n".join(lines)


def heartbeat_text(counts: dict) -> str:
    return (
        f"PulseFlow: fetched {counts.get('fetched', 0)} · matched {counts.get('matched', 0)} "
        f"· new {counts.get('new', 0)} · scored {counts.get('scored', 0)} · notified 0"
    )


def post_to_slack(webhook_url: str, text: str, client: httpx.Client | None = None) -> int:
    """Post one message. Slack returns the literal body 'ok' — status 200 is the signal."""
    c = client or httpx.Client(timeout=SLACK_TIMEOUT)
    try:
        return c.post(webhook_url, json={"text": text}).status_code
    finally:
        if client is None:
            c.close()


def notify(
    store: Store,
    counts: dict,
    *,
    webhook_url: str,
    min_score: int,
    heartbeat: bool,
    top_n: int = TOP_N,
    client: httpx.Client | None = None,
) -> int:
    """Return the number of jobs actually flipped to NOTIFIED (0 on a heartbeat)."""
    rows = store.fetch_notification_pool(min_score, top_n)

    if not rows:
        if heartbeat:
            status = post_to_slack(webhook_url, heartbeat_text(counts), client)
            if status != 200:
                raise RuntimeError(f"slack heartbeat failed status={status}")
            logger.info("heartbeat posted")
        return 0

    status = post_to_slack(webhook_url, build_message(rows), client)
    if status != 200:
        # Do not flip on a failed post — the rows stay SCORED and retry next run.
        raise RuntimeError(f"slack webhook failed status={status}")

    flipped = store.flip_to_notified([r["id"] for r in rows])
    if flipped != len(rows):
        logger.warning("CAS flipped fewer than posted", extra={"posted": len(rows), "flipped": flipped})
    logger.info("notified", extra={"posted": len(rows), "flipped": flipped})
    return flipped
