"""JobSource protocol + FreelancerRSS implementation (httpx fetch, feedparser parse).

Feed HTML is hostile input: descriptions are stripped to plain text at ingest
(SPEC.md Decision 20). A dead feed must be visible within one run: bozo, a
non-XML Content-Type, or zero entries from a non-empty body are feed errors,
not silent zeros (Decision 18). One malformed item never kills a fetch —
items parse individually with skip-and-log (Decision 9).
"""

import logging
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Protocol

import feedparser
import httpx

from pulseflow.models import Job, StageError

logger = logging.getLogger(__name__)

FEED_TIMEOUT = httpx.Timeout(30)


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()  # convert_charrefs=True decodes entities for free
        self.parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("script", "style"):
            self._skip_depth += 1
        self.parts.append(" ")  # tag boundary -> word gap

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style"):
            self._skip_depth = max(0, self._skip_depth - 1)
        self.parts.append(" ")

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self.parts.append(data)


def strip_html(raw: str) -> str:
    parser = _TextExtractor()
    parser.feed(raw)
    parser.close()
    return " ".join("".join(parser.parts).split())


class FeedError(Exception):
    """A feed-level failure: network, HTTP status, content type, or parse."""

    def __init__(self, url: str, kind: str, detail: str):
        self.url = url
        self.kind = kind
        self.detail = detail
        super().__init__(f"{kind}: {detail} ({url})")

    def to_stage_error(self) -> StageError:
        # Message text may embed the feed URL; store.py sanitizes before persisting.
        return StageError(stage="fetch", type=self.kind, message=str(self))


def parse_feed_bytes(data: bytes, url: str) -> list[Job]:
    """Parse one feed body. Raises FeedError on feed-level death; skips bad items."""
    parsed = feedparser.parse(data)
    if parsed.bozo:
        raise FeedError(url, "feed_parse_error", str(parsed.bozo_exception))
    if not parsed.entries:
        raise FeedError(url, "feed_empty", "0 entries from feed body")

    fetched_at = datetime.now(timezone.utc)
    jobs: list[Job] = []
    for entry in parsed.entries:
        guid = entry.get("id") or entry.get("link")  # feedparser maps <guid> to id
        title = entry.get("title")
        if not guid or not title:
            logger.warning(
                "skipping malformed feed item", extra={"feed": url, "has_guid": bool(guid)}
            )
            continue
        raw_description = entry.get("summary") or entry.get("description") or ""
        jobs.append(
            Job(
                guid=guid,
                url=entry.get("link"),
                title=strip_html(title),
                description=strip_html(raw_description),
                fetched_at=fetched_at,
            )
        )
    return jobs


def merge_keep_first(jobs: list[Job]) -> list[Job]:
    """In-memory dedupe layer 1: RSS feeds repeat GUIDs across keyword feeds."""
    seen: set[str] = set()
    merged: list[Job] = []
    for job in jobs:
        if job.guid not in seen:
            seen.add(job.guid)
            merged.append(job)
    return merged


class JobSource(Protocol):
    def fetch(self) -> tuple[list[Job], list[StageError]]:
        """Return (deduped jobs, feed-level errors). Never raises for one bad feed."""
        ...


class FreelancerRSS:
    def __init__(self, feed_urls: list[str], client: httpx.Client | None = None):
        self.feed_urls = feed_urls
        self._client = client

    def _fetch_one(self, client: httpx.Client, url: str) -> list[Job]:
        response = client.get(url, follow_redirects=True)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if "xml" not in content_type:
            raise FeedError(url, "feed_content_type", f"non-XML content type: {content_type}")
        return parse_feed_bytes(response.content, url)

    def fetch(self) -> tuple[list[Job], list[StageError]]:
        jobs: list[Job] = []
        errors: list[StageError] = []
        client = self._client or httpx.Client(timeout=FEED_TIMEOUT)
        try:
            for url in self.feed_urls:
                try:
                    feed_jobs = self._fetch_one(client, url)
                except FeedError as exc:
                    logger.error("feed error", extra={"feed": url, "kind": exc.kind})
                    errors.append(exc.to_stage_error())
                except httpx.HTTPError as exc:
                    logger.error("feed http error", extra={"feed": url, "kind": type(exc).__name__})
                    errors.append(
                        FeedError(url, type(exc).__name__, str(exc)).to_stage_error()
                    )
                else:
                    jobs.extend(feed_jobs)
                    logger.info("feed fetched", extra={"feed": url, "items": len(feed_jobs)})
        finally:
            if self._client is None:
                client.close()
        return merge_keep_first(jobs), errors
