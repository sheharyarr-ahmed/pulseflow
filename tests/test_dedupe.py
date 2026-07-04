"""dedupe.py: batched GUID lookup + seen-removal, including URL-shaped GUIDs."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

from pulseflow.dedupe import find_existing_guids, remove_seen
from pulseflow.models import Job

NOW = datetime(2026, 7, 4, tzinfo=timezone.utc)


def _client_returning_per_chunk(chunks_data):
    """Mock whose .in_(...).execute() yields the next queued chunk's rows."""
    client = MagicMock()
    builder = MagicMock()
    client.table.return_value = builder
    builder.select.return_value = builder
    builder.in_.return_value = builder
    builder.execute.side_effect = [MagicMock(data=rows) for rows in chunks_data]
    return client, builder


def job(guid: str) -> Job:
    return Job(guid=guid, title="t", fetched_at=NOW)


def test_find_existing_guids_single_chunk():
    client, builder = _client_returning_per_chunk([[{"guid": "a"}, {"guid": "c"}]])
    existing = find_existing_guids(client, ["a", "b", "c"])
    assert existing == {"a", "c"}
    builder.in_.assert_called_once_with("guid", ["a", "b", "c"])


def test_chunks_at_100():
    guids = [f"g{i}" for i in range(250)]
    client, builder = _client_returning_per_chunk([[], [], []])
    find_existing_guids(client, guids)
    assert builder.in_.call_count == 3  # 100 + 100 + 50
    assert [len(c.args[1]) for c in builder.in_.call_args_list] == [100, 100, 50]


def test_empty_guids_makes_no_query():
    client = MagicMock()
    assert find_existing_guids(client, []) == set()
    client.table.assert_not_called()


def test_url_shaped_guid_passes_through_unmodified():
    url_guid = "https://www.freelancer.com/projects/foo,(bar)"
    client, builder = _client_returning_per_chunk([[{"guid": url_guid}]])
    existing = find_existing_guids(client, [url_guid])
    assert existing == {url_guid}
    assert builder.in_.call_args.args[1] == [url_guid]  # not escaped/altered by us


def test_remove_seen_preserves_order_and_drops_known():
    client, _ = _client_returning_per_chunk([[{"guid": "b"}]])
    kept = remove_seen(client, [job("a"), job("b"), job("c")])
    assert [j.guid for j in kept] == ["a", "c"]


def test_remove_seen_empty():
    client = MagicMock()
    assert remove_seen(client, []) == []
    client.table.assert_not_called()
