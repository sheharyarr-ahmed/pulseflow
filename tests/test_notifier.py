"""notifier.py: one message, top<=3, threshold/staleness pool, heartbeat, CAS flip.

Webhook is mocked with httpx.MockTransport; the store is a fake exposing the two
methods notify() calls, so pool filtering and the CAS flip are asserted directly.
"""

import httpx
import pytest

from pulseflow.notifier import (
    build_message,
    escape_mrkdwn,
    heartbeat_text,
    notify,
    truncate_reasoning,
)

WEBHOOK = "https://hooks.slack.com/services/T/B/secret"


# --- pure helpers -----------------------------------------------------------

def test_escape_mrkdwn_handles_link_breaking_chars():
    assert escape_mrkdwn("Tom & Jerry <script>") == "Tom &amp; Jerry &lt;script&gt;"


def test_truncate_reasoning_collapses_and_caps():
    assert truncate_reasoning("a\n\n  b   c") == "a b c"
    long = "x" * 200
    out = truncate_reasoning(long)
    assert len(out) == 140 and out.endswith("…")


def test_build_message_one_line_per_job_with_link_and_score():
    rows = [
        {"title": "Next.js MVP", "url": "https://f.com/1", "score": 9, "reasoning": "direct match"},
        {"title": "AI agent", "url": None, "score": 8, "reasoning": "strong"},
    ]
    msg = build_message(rows)
    assert msg.splitlines()[0] == "• <https://f.com/1|Next.js MVP> — *9/10* — direct match"
    assert msg.splitlines()[1] == "• AI agent — *8/10* — strong"  # no link when url missing


def test_build_message_escapes_hostile_title():
    msg = build_message([{"title": "A & B <x>", "url": "https://f.com/1", "score": 7, "reasoning": "r"}])
    assert "A &amp; B &lt;x&gt;" in msg


def test_heartbeat_text_format():
    assert heartbeat_text({"fetched": 10, "matched": 4, "new": 2, "scored": 2}) == (
        "PulseFlow: fetched 10 · matched 4 · new 2 · scored 2 · notified 0"
    )


# --- notify() with fake store + mocked webhook ------------------------------

class FakeStore:
    def __init__(self, pool):
        self._pool = pool
        self.flipped_ids = None

    def fetch_notification_pool(self, min_score, top_n, hours=24):
        return self._pool[:top_n]

    def flip_to_notified(self, ids):
        self.flipped_ids = list(ids)
        return len(ids)  # simulate all still SCORED


def capturing_client(status=200):
    posts = []

    def handler(request: httpx.Request) -> httpx.Response:
        posts.append(request)
        return httpx.Response(status, text="ok")

    return httpx.Client(transport=httpx.MockTransport(handler)), posts


def rows(n):
    return [
        {"id": f"id-{i}", "title": f"job {i}", "url": f"https://f.com/{i}", "score": 9 - i, "reasoning": "r"}
        for i in range(n)
    ]


def test_posts_one_message_and_flips_exactly_posted():
    store = FakeStore(rows(5))
    client, posts = capturing_client()
    flipped = notify(store, {}, webhook_url=WEBHOOK, min_score=7, heartbeat=True, client=client)
    assert len(posts) == 1                       # ONE webhook message
    assert flipped == 3                          # top_n cap
    assert store.flipped_ids == ["id-0", "id-1", "id-2"]
    body = posts[0].read().decode()
    assert body.count("•") == 3                  # three job lines in one payload


def test_heartbeat_when_pool_empty():
    store = FakeStore([])
    client, posts = capturing_client()
    flipped = notify(
        store, {"fetched": 8, "matched": 0, "new": 0, "scored": 0},
        webhook_url=WEBHOOK, min_score=7, heartbeat=True, client=client,
    )
    assert flipped == 0
    assert len(posts) == 1
    assert "notified 0" in posts[0].read().decode()
    assert store.flipped_ids is None             # nothing flipped on a heartbeat


def test_no_heartbeat_when_disabled_and_empty():
    store = FakeStore([])
    client, posts = capturing_client()
    flipped = notify(store, {}, webhook_url=WEBHOOK, min_score=7, heartbeat=False, client=client)
    assert flipped == 0 and posts == []          # silent


def test_failed_post_does_not_flip():
    store = FakeStore(rows(2))
    client, _ = capturing_client(status=500)
    with pytest.raises(RuntimeError):
        notify(store, {}, webhook_url=WEBHOOK, min_score=7, heartbeat=True, client=client)
    assert store.flipped_ids is None             # rows stay SCORED, retry next run


class CASMismatchStore(FakeStore):
    def flip_to_notified(self, ids):
        self.flipped_ids = list(ids)
        return len(ids) - 1  # one row was already NOTIFIED by a racing run


def test_cas_mismatch_warns_but_returns_flipped_count(caplog):
    store = CASMismatchStore(rows(3))
    client, _ = capturing_client()
    flipped = notify(store, {}, webhook_url=WEBHOOK, min_score=7, heartbeat=True, client=client)
    assert flipped == 2  # returns actual flipped, not posted
