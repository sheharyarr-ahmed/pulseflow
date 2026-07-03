"""Fetcher tests against committed fixtures — CI never touches the network.

Fixtures: recorded real Freelancer XML, HTML-with-200 (feed error, not silent
zero), empty body, missing GUIDs (skip-and-log, URL fallback).
"""

from pathlib import Path

import httpx
import pytest

from pulseflow.fetcher import (
    FeedError,
    FreelancerRSS,
    merge_keep_first,
    parse_feed_bytes,
    strip_html,
)

FIXTURES = Path(__file__).parent / "fixtures"
FEED_URL = "https://www.freelancer.com/rss.xml?keyword=react"


def fixture_bytes(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


# --- strip_html -------------------------------------------------------------

def test_strip_html_removes_tags_and_decodes_entities():
    raw = "<p>Budget: &amp; up to <b>$500</b></p><script>alert('x')</script>tail"
    assert strip_html(raw) == "Budget: & up to $500 tail"


def test_strip_html_inserts_word_gaps_at_tag_boundaries():
    assert strip_html("<p>one</p><p>two</p>") == "one two"


# --- parse_feed_bytes on fixtures --------------------------------------------

def test_recorded_real_feed_parses():
    jobs = parse_feed_bytes(fixture_bytes("freelancer_react.xml"), FEED_URL)
    assert len(jobs) == 20
    assert all(j.guid.startswith("Freelancer_project_") for j in jobs)
    assert all(j.title and "<" not in j.description for j in jobs)
    assert all(j.fetched_at.tzinfo is not None for j in jobs)


def test_html_with_200_is_a_parse_error_not_silent_zero():
    with pytest.raises(FeedError) as exc:
        parse_feed_bytes(fixture_bytes("html_200.html"), FEED_URL)
    assert exc.value.kind in ("feed_parse_error", "feed_empty")


def test_empty_body_is_a_feed_error():
    with pytest.raises(FeedError):
        parse_feed_bytes(fixture_bytes("empty.xml"), FEED_URL)


def test_missing_guid_fallback_and_skip():
    jobs = parse_feed_bytes(fixture_bytes("missing_guids.xml"), FEED_URL)
    # item 1: guid kept; item 2: falls back to link URL;
    # item 3 (no guid+link) and item 4 (no title): skipped.
    assert [j.guid for j in jobs] == [
        "Freelancer_project_1",
        "https://www.freelancer.com/projects/2",
    ]
    assert jobs[0].description == "Build a React dashboard"


# --- merge + FreelancerRSS over a mock transport ------------------------------

def test_merge_keep_first():
    jobs = parse_feed_bytes(fixture_bytes("missing_guids.xml"), FEED_URL)
    merged = merge_keep_first(jobs + jobs)
    assert len(merged) == len(jobs)


def _transport(responses: dict[str, httpx.Response]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        return responses[str(request.url)]

    return httpx.MockTransport(handler)


def test_fetch_merges_feeds_and_dedupes_across_them():
    xml = fixture_bytes("freelancer_react.xml")
    urls = ["https://feeds.test/a", "https://feeds.test/b"]
    client = httpx.Client(
        transport=_transport(
            {u: httpx.Response(200, content=xml, headers={"content-type": "text/xml"}) for u in urls}
        )
    )
    jobs, errors = FreelancerRSS(urls, client=client).fetch()
    assert errors == []
    assert len(jobs) == 20  # same 20 items in both feeds -> keep-first


def test_one_broken_feed_logs_and_continues():
    xml = fixture_bytes("freelancer_react.xml")
    client = httpx.Client(
        transport=_transport(
            {
                "https://feeds.test/ok": httpx.Response(
                    200, content=xml, headers={"content-type": "text/xml"}
                ),
                "https://feeds.test/html": httpx.Response(
                    200,
                    content=fixture_bytes("html_200.html"),
                    headers={"content-type": "text/html"},
                ),
                "https://feeds.test/500": httpx.Response(500, content=b"boom"),
            }
        )
    )
    jobs, errors = FreelancerRSS(
        ["https://feeds.test/ok", "https://feeds.test/html", "https://feeds.test/500"],
        client=client,
    ).fetch()
    assert len(jobs) == 20
    assert {e.type for e in errors} == {"feed_content_type", "HTTPStatusError"}
    assert all(e.stage == "fetch" for e in errors)


def test_all_feeds_dead_returns_zero_jobs_and_errors():
    client = httpx.Client(
        transport=_transport({"https://feeds.test/dead": httpx.Response(410, content=b"gone")})
    )
    jobs, errors = FreelancerRSS(["https://feeds.test/dead"], client=client).fetch()
    assert jobs == [] and len(errors) == 1
