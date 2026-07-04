# PulseFlow architecture

## Pipeline

One daily GitHub Actions run executes a linear pipeline. Each stage is independently re-runnable; the three-status enum on `jobs` (`NEW → SCORED → NOTIFIED`) is the sole idempotency mechanism.

```
fetch → filter → dedupe → persist NEW → score → notify → finalize run
```

| Stage | Module | What it does |
|-------|--------|--------------|
| fetch | `fetcher.py` | Freelancer keyword RSS via httpx (30s timeout), parsed with feedparser. Feed-death detection (bozo / non-XML content-type / zero entries from a non-empty body) surfaces as a recorded error, not a silent zero. HTML stripped to plain text at ingest. In-memory keep-first dedupe across keyword feeds. |
| filter | `filters.py` | Case-insensitive, word-boundary keyword match on title + description; ANY match passes. Driven entirely by `config/keywords.json`. |
| dedupe | `dedupe.py` | One batched `SELECT guid IN (...)` against Supabase removes already-seen GUIDs **before** scoring, so the LLM never re-scores a job. |
| persist | `store.py` | Surviving jobs upserted `NEW` with `on_conflict=guid, ignore_duplicates` — the unique constraint is a backstop, not a crash source; `jobs_new` counts rows actually inserted. |
| score | `scorer.py` | `SELECT ... WHERE status='NEW' AND score_attempts < 6 LIMIT cap` — one query covers this run's inserts and any leftovers from a prior degraded run. Each job scored 1–10 by `claude-haiku-4-5` via `messages.parse` structured output; each success is a per-row `UPDATE` to `SCORED`, so a mid-run crash loses at most one job's work. |
| notify | `notifier.py` | Top ≤3 `SCORED` rows above `min_score` from the last 24h, one Slack message, then a compare-and-swap flip to `NOTIFIED`. A quiet run posts a heartbeat instead, so silence always means breakage. |
| finalize | `workflow.py` | Every run writes a `workflow_runs` row (inserted at start, finalized in try/finally with counts, sanitized errors, and duration). This is the observability trail. |

## Failure model

- **LLM failure degrades.** After two per-run attempts a job stays `NEW`, the error is logged, and the run exits 0 — the next run's candidate query retries it (up to a lifetime cap of 6 attempts, after which the row is derived as "gave up"). A Slack outage is treated the same way: the posted rows stay `SCORED` and re-post next run within the 24h window.
- **Infrastructure failure fails red.** Fetch failure (all feeds dead) or any Supabase read/write failure exits 1 — broken plumbing must show a red run, or the "3 consecutive green days" success gate is meaningless. A single dead feed among several is logged and the run continues.
- **Secrets never reach a public surface.** `workflow_runs.errors` is world-readable via anon SELECT, so every persisted message is sanitized (URLs stripped — the Slack webhook URL *is* the credential), only the exception type name kept, length capped. Config and logging never print env values.

## Dashboard

Next.js App Router on Vercel, reading Supabase directly with the publishable key under a read-only RLS policy — no backend of our own. Server Components with 5-minute ISR (`revalidate = 300`); data changes once a day. Every query has an explicit `.order().limit()` because supabase-js silently truncates at 1,000 rows. Timestamps render server-side in `Asia/Karachi` with an explicit "PKT" label (deterministic, no hydration mismatch). Feed text renders as text only — never `dangerouslySetInnerHTML` — because anyone can post a Freelancer job, so raw HTML would be a stored-XSS vector.

## Honest limitations

See the README's "Honest caveats" section: GitHub Actions cron delay and dropped ticks, the 60-day auto-disable and its self-re-enable mitigation, the Supabase free-tier pause cascade, API-credit mortality, and Freelancer's narrow keyword matching.

## Scaling path

The pipeline is deliberately linear — no graph framework, no queue, no background-job infrastructure. If this ever needed to scale (multiple users, many sources, sub-hourly cadence), the natural evolution is: swap the `JobSource` protocol for multiple concrete sources (a second implementation, e.g. the Remotive API, was verified as a working fallback but is documented-not-built — 24h-delayed data, salaried-remote job class, attribution obligations); move orchestration to a durable job runner (Inngest or similar) for retries and fan-out; and add per-tenant partitioning. None of that is warranted at personal-use scale, and shipping it now would be speculative complexity.
