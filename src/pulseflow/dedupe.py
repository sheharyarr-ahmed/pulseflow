"""Batched GUID lookup against Supabase — dedupe layer 2 (SPEC.md Decision 3).

Layer 1 (in-memory keep-first across keyword feeds) already ran in the fetcher.
This removes GUIDs already resident in the DB BEFORE scoring, so Claude never
re-scores a seen job. Chunked because .in_() encodes the list into the query
string; URL-fallback GUIDs may contain PostgREST-reserved characters, which
postgrest-py quotes for us.
"""

import logging

CHUNK_SIZE = 100

logger = logging.getLogger(__name__)


def find_existing_guids(client, guids: list[str], chunk_size: int = CHUNK_SIZE) -> set[str]:
    """Return the subset of `guids` already present in the jobs table."""
    existing: set[str] = set()
    for start in range(0, len(guids), chunk_size):
        chunk = guids[start : start + chunk_size]
        if not chunk:
            continue
        res = client.table("jobs").select("guid").in_("guid", chunk).execute()
        existing.update(row["guid"] for row in (res.data or []))
    return existing


def remove_seen(client, jobs, chunk_size: int = CHUNK_SIZE):
    """Filter out jobs whose GUID is already stored. Preserves order."""
    if not jobs:
        return []
    existing = find_existing_guids(client, [j.guid for j in jobs], chunk_size)
    return [j for j in jobs if j.guid not in existing]
