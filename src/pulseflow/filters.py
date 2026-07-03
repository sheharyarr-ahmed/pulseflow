"""Pure keyword filter: word-boundary match on title + description.

Case-insensitive, ANY-match passes (SPEC.md Goal step 3). Lookaround boundaries
instead of \\b so keywords that start or end with non-word characters
("Next.js", future "C#") still anchor correctly; literal spaces in a keyword
match any whitespace run ("AI agent" matches across a newline).
"""

import re

from pulseflow.models import Job


def _keyword_pattern(keyword: str) -> re.Pattern[str]:
    escaped = re.escape(keyword).replace("\\ ", r"\s+")
    return re.compile(rf"(?<!\w){escaped}(?!\w)", re.IGNORECASE)


def compile_keywords(keywords: list[str]) -> list[re.Pattern[str]]:
    return [_keyword_pattern(k) for k in keywords]


def matches_any(job: Job, patterns: list[re.Pattern[str]]) -> bool:
    haystack = f"{job.title or ''} {job.description}"
    return any(p.search(haystack) for p in patterns)


def filter_jobs(jobs: list[Job], keywords: list[str]) -> list[Job]:
    patterns = compile_keywords(keywords)
    return [job for job in jobs if matches_any(job, patterns)]
