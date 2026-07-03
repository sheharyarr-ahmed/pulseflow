# PulseFlow · SPEC.md

Code-first workflow orchestration that replaces a Zapier subscription for one real use case: a daily freelance-market job hunt. Portfolio project for SheryLabs. Personal-use scale, production-grade discipline.

Owner: Sheharyar Ahmed. Single author on every commit. Zero cash spend beyond existing Anthropic API credits.

This spec supersedes the original idea document. It incorporates the results of a pre-build analysis (July 2026) that live-verified data sources, platform limits, and API patterns. Where the original doc and this spec disagree, this spec wins.

---

## ⚠️ Provisional owner decisions (confirm before Phase 1)

Four decisions were made on recommended defaults while the owner was AFK. Each is defensible, but each is the owner's call. Flip any of them by editing this section and the referenced Decision before implementation starts.

| # | Decision taken | Alternative you can flip to |
|---|----------------|------------------------------|
| P1 | **Freelancer.com RSS is the primary job source**, and all public claims rebrand from "Upwork job-hunt automation" to "freelance-market job-hunt automation." Upwork public RSS is dead — verified live July 2026: `410 Gone` on `/ab/feed/jobs/rss` variants, Cloudflare 403 on `/nx/search/jobs/rss` (see Decision 5). | Keep the Upwork framing as a "demonstration of the pattern" instead of "my real daily hunt" — weaker story, zero fabrication risk if you won't actually bid on Freelancer.com. Reopening the Upwork official API is NOT recommended (partner approval + OAuth, indefinite stall). |
| P2 | **Scoring rubric is stack-fit only** (no rate/budget signals), with reasoning instructed to stay neutral because it renders on a public dashboard. `min_score = 7` with a week-one calibration review. | Add budget heuristics (e.g. deprioritize sub-$500 fixed-price) — supply your floor; it stays out of the public reasoning text. Or write the rubric body yourself at Phase 1. |
| P3 | **Duplicate-over-drop notification semantics**: post one Slack message, then compare-and-swap the status flip. A crash between post and flip may rarely re-post. The original "never double-posts" invariant is amended to "no duplicates in normal operation." | Drop-over-duplicate (flip first, then post): strict never-double-post, but a Slack failure after the flip silently loses those notifications forever. For a job-hunt tool, a missed notification costs a bid; a duplicate to an audience of one costs nothing — hence the default. |
| P4 | **`.claude/` ships as the load-bearing subset** of the reference architecture: `settings.json`, `CLAUDE.md`, `verify.sh`, gitignore entries; `agents/pipeline-debugger.md` lands at Phase 4. No `rules/`, `skills/`, or `.mcp.json` until something earns them (Simplicity First). | Full reference structure (rules/, skills/, .mcp.json, CLAUDE.local.md placeholders) at scaffold time — maximum fidelity to the reference image, at the cost of committed placeholder files in a public repo. |

---

## Goal

Ship a working, publicly inspectable automation platform that runs unattended every day and proves the Zapier-replacement skill class on the SheryLabs profile.

The system, end to end:

1. GitHub Actions cron fires daily at **08:17 UTC** (13:17 PKT, inside the Window 1 hunt time). Off-peak minute chosen deliberately: GitHub documents that on-the-hour schedules are delayed or dropped under load.
2. A Python 3.13 script fetches new freelance job postings from **Freelancer.com keyword RSS feeds** (`https://www.freelancer.com/rss.xml?keyword=<kw>`), one fetch per broad keyword, merged and de-duplicated in-memory by GUID. The fetcher sits behind a `JobSource` protocol so the source can swap without touching any downstream stage.
3. Jobs are filtered against a configurable keyword list from `config/keywords.json` — case-insensitive, word-boundary match on title + description, ANY-match passes. Nothing hardcoded.
4. Already-seen jobs are removed by a single batched GUID lookup against Supabase BEFORE scoring, so Claude never re-scores a job.
5. Surviving jobs are **persisted immediately with status NEW** (upsert on GUID conflict, ignore duplicates). Data capture never depends on the LLM being up.
6. The scoring candidate set is `SELECT ... WHERE status='NEW' AND score_attempts < 6 LIMIT max_jobs_scored_per_run` — one query covers this run's inserts AND leftovers from any prior degraded run. Each job is scored 1–10 by `claude-haiku-4-5` via structured output (`client.messages.parse` with a Pydantic `ScoreResult`); each scored row is UPDATEd to SCORED individually, so a mid-run crash loses at most one job's work.
7. The notifier selects up to 3 rows `WHERE status='SCORED' AND score >= min_score AND scored_at >= now() - interval '24 hours'`, ordered by score DESC then fetched_at DESC, posts ONE Slack webhook message, then flips exactly the posted rows with a compare-and-swap update. On a day with nothing to post, it posts a one-line heartbeat instead (config-togglable), so silence always means breakage, never a quiet day.
8. Every run writes one row to `workflow_runs` — inserted at run start (started_at only), finalized in a try/finally with counts, sanitized errors, and duration. This is the observability trail.
9. A Next.js (latest stable, App Router) dashboard on Vercel reads Supabase directly with the publishable key under a read-only RLS policy. Server Components + 5-minute ISR. No FastAPI. No server of our own.

Success is defined as: the cron has run green for 3 consecutive days in production, the dashboard renders live data at a public Vercel URL, the repo is public with clean single-author history, and the README documents the architecture honestly — including the Actions cron-delay caveat, the 60-day auto-disable rule and its self-re-enable mitigation, and the Supabase pause cascade.

Cost model: $0 infrastructure (GitHub Actions free minutes, Supabase free tier, Vercel Hobby, Slack free workspace). Only spend is Anthropic API usage on existing credits — well under $1/month at Haiku pricing ($1/$5 per MTok) for 10–30 new jobs/day, hard-capped by `max_jobs_scored_per_run`.

Manual steps rule: any step that requires a browser or a human (Supabase project creation, Slack webhook, API keys, GitHub secrets, Vercel link, repo metadata) is a STOP point. The session halts, prints exact instructions, and waits. Never fabricate a secret; never scaffold around a missing credential.

---

## Files

```
pulseflow/
├── .github/
│   └── workflows/
│       ├── daily-hunt.yml          # cron 17 8 * * *, workflow_dispatch, concurrency group,
│       │                           #   timeout-minutes: 10, permissions {contents: read, actions: write},
│       │                           #   setup-uv + uv sync --locked, final self-re-enable step
│       └── ci.yml                  # pytest -q on push/PR (portfolio green-check discipline)
├── .githooks/
│   └── commit-msg                  # rejects claude / co-authored-by / generated with / anthropic (case-insensitive)
├── .claude/
│   ├── settings.json               # permissions only, NO hooks (see Decision 16)
│   ├── CLAUDE.md                   # ~16 lines: stack locks, invariants, commands, feed-status line
│   ├── verify.sh                   # chmod +x; dirty-tree early-exit; hooksPath assertion; .venv/bin/pytest -q
│   └── agents/                     # created at Phase 4 with pipeline-debugger.md — NOT at scaffold time
├── config/
│   └── keywords.json               # feeds, filter keywords, min_score, heartbeat, per-run cap
├── src/
│   └── pulseflow/
│       ├── __init__.py
│       ├── models.py               # Pydantic v2: Job, ScoreResult, WorkflowRun, JobStatus enum
│       ├── config.py               # env fail-fast + keywords.json via Pydantic; never logs env VALUES
│       ├── fetcher.py              # JobSource protocol + FreelancerRSS impl; httpx fetch, feedparser parse
│       ├── filters.py              # pure function: word-boundary keyword match on title + description
│       ├── dedupe.py               # batched SELECT guid IN (...) against Supabase
│       ├── scorer.py               # messages.parse structured output, per-run retry 2, lifetime cap 6
│       ├── store.py                # upsert-on-guid-conflict inserts; run-row insert-first/finalize; error sanitizer
│       ├── notifier.py             # one Slack message, top ≤3, heartbeat, compare-and-swap flip
│       ├── logging_setup.py        # structured JSON to stdout (Actions captures it)
│       ├── workflow.py             # orchestrator: fetch → filter → dedupe → persist NEW → score → notify
│       └── prompts/
│           └── scoring.md          # versioned scoring prompt: profile block + band anchors
├── scripts/
│   └── run_hunt.py                 # entry point for cron and by hand; --dry-run flag
├── db/
│   └── schema.sql                  # jobs + workflow_runs, indexes, CHECK constraints, RLS policies
├── dashboard/                      # Next.js latest stable, App Router, deployed to Vercel (root dir = dashboard/)
│   ├── app/
│   │   ├── page.tsx                # score history + pipeline funnel stats
│   │   ├── runs/page.tsx           # workflow run log (last 90 days)
│   │   ├── jobs/[id]/page.tsx      # single job: score, full reasoning, snippet + outbound source link
│   │   └── error.tsx               # 'data source unreachable' state (Supabase paused ≠ broken portfolio page)
│   ├── lib/supabase.ts             # publishable-key server client, read-only via RLS
│   └── package.json
├── tests/
│   ├── test_models.py
│   ├── test_config.py              # parses the REAL config/keywords.json through the Pydantic model
│   ├── test_fetcher.py             # fixtures: recorded Freelancer XML, HTML-with-200, empty body, missing GUIDs
│   ├── test_filters.py
│   ├── test_dedupe.py
│   ├── test_scorer.py              # mocked client: success, retry-then-success, double-failure → degradation
│   ├── test_notifier.py            # mocked webhook: top-3, threshold, staleness window, heartbeat, CAS flip
│   ├── test_store.py               # error sanitizer: SLACK_WEBHOOK_URL never appears in serialized errors
│   └── test_workflow.py            # full pipeline, all externals mocked
├── docs/
│   └── ARCHITECTURE.md             # pipeline diagram, honest limitations, scaling path
├── .env.example                    # every required var, no real values
├── .gitignore                      # .env, .venv, __pycache__, node_modules, .vercel,
│                                   #   .claude/settings.local.json, .claude/CLAUDE.local.md
├── LICENSE                         # MIT, Sheharyar Ahmed
├── pyproject.toml                  # Python 3.13, hatchling, src layout; deps below
├── uv.lock                         # committed — reproducible unattended cron runs
└── README.md                       # hero summary, Mermaid diagram, setup, honest caveats
```

Python dependencies (`pyproject.toml`): `feedparser`, `httpx`, `pydantic`, `anthropic`, `supabase`, `python-dotenv`; dev: `pytest`. Tooling: **uv** with committed `uv.lock`; CI uses `astral-sh/setup-uv`, `uv sync --locked`, `uv run`.

### config/keywords.json shape

```json
{
  "feed_urls": [
    "https://www.freelancer.com/rss.xml?keyword=react",
    "https://www.freelancer.com/rss.xml?keyword=python",
    "https://www.freelancer.com/rss.xml?keyword=mobile%20app",
    "https://www.freelancer.com/rss.xml?keyword=ai"
  ],
  "keywords": ["AI agent", "Next.js", "MVP", "SaaS", "iOS", "agentic", "RAG", "LangGraph"],
  "min_score": 7,
  "heartbeat": true,
  "max_jobs_scored_per_run": 50
}
```

Feed-level keywords are deliberately broad (Freelancer's keyword matching is narrow — `nextjs` returns 0 items while `react` returns 20); `keywords` does the precise local filtering. `feed_urls` lives here, not in env — it is not a secret, and this file is the designated editable-without-code surface.

### Supabase schema (`db/schema.sql`)

- `jobs`: `id uuid pk default gen_random_uuid()`, `guid text unique not null`, `source text not null default 'freelancer'`, `url text`, `title text`, `description text` (plain text — HTML stripped at ingest), `score smallint null CHECK (score BETWEEN 1 AND 10)`, `reasoning text null`, `status text not null CHECK (status IN ('NEW','SCORED','NOTIFIED'))`, `score_attempts smallint not null default 0`, `fetched_at timestamptz not null`, `scored_at timestamptz null`, `notified_at timestamptz null`. Index on `guid`, index on `status`.
- `workflow_runs`: `id uuid pk`, `started_at timestamptz not null`, `finished_at timestamptz null`, `jobs_fetched int`, `jobs_filtered int`, `jobs_new int`, `jobs_scored int`, `jobs_notified int`, `errors jsonb` (array of `{stage, type, message}` — messages sanitized, see Decision 19), `duration_seconds numeric`.
- RLS enabled on both tables. Publishable (anon) role: SELECT only. All writes go through the secret key, which lives only in GitHub Actions secrets, never in the dashboard.
- Exactly three statuses. Staleness and give-up states are derived (`scored_at` age, `score_attempts >= 6`), not new enum values.

### Secrets (STOP points, current key format)

Supabase legacy `anon`/`service_role` JWT keys are deprecated end-2026; use the replacement opaque keys from day one:

| Var | Where | Notes |
|-----|-------|-------|
| `ANTHROPIC_API_KEY` | Actions secret + local `.env` | asked for at Phase 1 first live call, not before |
| `SUPABASE_URL` | Actions secret + local `.env` + dashboard `NEXT_PUBLIC_SUPABASE_URL` | |
| `SUPABASE_SECRET_KEY` | Actions secret + local `.env` ONLY | `sb_secret_…`; write-capable; never under `dashboard/` |
| `SLACK_WEBHOOK_URL` | Actions secret + local `.env` | the URL IS the credential — see Decision 19 |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | Vercel env | `sb_publishable_…`; safe by RLS design |

Confirm actual key names/formats at the Phase 2 STOP point — the Supabase dashboard shows both legacy and new keys during the transition.

---

## Approach & Decisions

Original decisions 1–13 stand except where amended below. Every decision logs the alternative considered, so it is defensible from memory in a vetting call.

1. **No FastAPI backend.** (unchanged) Supabase already exposes a REST layer with RLS; a second deployment surface adds cold starts for zero capability.
2. **GUID-based idempotency, not run-level locking** (amended). GUID dedupe makes every stage re-runnable. Two additions close the gaps the original left open: (a) `concurrency: { group: daily-hunt, cancel-in-progress: false }` in `daily-hunt.yml` queues a manual dispatch behind a running cron instead of letting them interleave — queueing, unlike a lock, can never wedge a retry; (b) inserts are `upsert(on_conflict="guid", ignore_duplicates=True)` so the unique constraint is a backstop, not a crash source, and `jobs_new` counts rows actually inserted.
3. **Dedupe before scoring** (amended): batch dedupe is two layers — in-memory keep-first by GUID within the fetched batch (RSS feeds repeat GUIDs across keyword feeds and regenerations), then ONE batched `SELECT guid IN (...)` against Supabase. Claude only ever sees genuinely new jobs.
4. **Status enum drives notification idempotency** (unchanged in shape): NEW → SCORED → NOTIFIED, three states forever. The notifier's flip is a compare-and-swap (`UPDATE ... SET status='NOTIFIED', notified_at=now() WHERE id IN (...) AND status='SCORED'`).
5. **Freelancer.com RSS is the primary source; the JobSource protocol stays** (amended — was "Upwork with fallback contingency"). Live verification July 2026: Upwork `/ab/feed/jobs/rss` → HTTP 410 with branded 404 HTML; `/ab/feed/topics/rss`, `/ab/feed/jobs/atom` → identical 410; `/nx/search/jobs/rss` → 403 Cloudflare challenge. Freelancer keyword RSS → 200 `text/xml`, 20 items, stable `<guid isPermaLink="false">Freelancer_project_NNNN</guid>` — an ideal dedupe key. This evidence gets logged in `.claude/CLAUDE.md` as the Phase 1 validation result. Remotive API was verified as a working secondary (structured JSON, search param) but is documented-not-built: 24h-delayed data, salaried-remote job class, attribution obligations. README states the source honestly; personal once-daily RSS consumption is normal use, and the dashboard shows snippets + outbound links, not wholesale republication (Decision 20).
6. **Haiku for scoring, no Opus anywhere** (amended with specifics): model `claude-haiku-4-5` set in `config.py` with env override. Structured output via `client.messages.parse(output_format=ScoreResult)` — the current SDK pattern; forced tool-use is the legacy mechanism. `ScoreResult(score: int [ge=1, le=10], reasoning: str)`; JSON-schema numeric bounds are stripped server-side, so Pydantic client-side validation is the real gate — a `ValidationError`, refusal, or `max_tokens` stop counts as a failed attempt. `max_tokens≈256`, no `effort` param (Haiku 4.5 rejects it), no temperature override.
7. **Graceful degradation over hard failure — for the LLM only** (amended). Anthropic failure after 2 attempts: job stays NEW, run logs the error, exits 0; the next run's candidate query picks it up. Fetch or Supabase failure: best-effort `workflow_runs` finalize, then **exit 1** — broken plumbing must show a red run, or the "3 green days" gate is meaningless. Two caps bound the degradation loop: per-run retry of 2 attempts, and a lifetime `score_attempts` cap of 6 (3 runs' worth), after which the row is excluded from the candidate query — no new status, the dashboard derives "gave up" from the counter. Credits exhaustion is visible within a day via the heartbeat (`scored 0, new > 0` for consecutive days) and documented in ARCHITECTURE.md.
8. **GitHub Actions cron, with ALL its failure modes documented and mitigated** (amended). Cron `17 8 * * *` (off-peak minute — GitHub documents delays and outright dropped ticks at the top of the hour). The 60-day inactivity auto-disable is mitigated by the workflow's final step re-enabling itself: `gh api -X PUT repos/${{ github.repository }}/actions/workflows/daily-hunt.yml/enable` with `permissions: {contents: read, actions: write}` — zero commits, no third-party action (the popular keepalive action makes bot commits that would violate single-author history, and its repo was disabled by GitHub staff). `timeout-minutes: 10` on the job; `httpx.Timeout(30)` on feed and Slack calls — a wedged connection must not become a 6-hour hang that overlaps the next cron. The cascade (Actions dies → no DB traffic → Supabase pauses after ~7 days → dashboard dies) is documented in ARCHITECTURE.md; the daily run itself is the Supabase keepalive.
9. **Python 3.13, Pydantic v2 at every boundary** (amended with granularity): feed items parse individually with skip-and-log — one malformed item never kills a fetch. Items must have a non-empty GUID; fall back to the job URL when absent. `test_config.py` parses the real `keywords.json` in CI, so a malformed config edit can never reach the cron.
10. **Vercel + Supabase free tiers** (unchanged; limits verified comfortable). Hobby is non-commercial personal use — a portfolio qualifies; repo stays on the personal GitHub account (Hobby cannot link org repos). Vercel runtime logs retain 1 hour on Hobby, which is exactly why observability lives in `workflow_runs` + Actions logs.
11. **Attribution discipline is mechanical** (unchanged): `.githooks/commit-msg` rejects claude / co-authored-by / generated with / anthropic (case-insensitive); `git config core.hooksPath .githooks` before the first commit; author locked to Sheharyar Ahmed <sheharyar.softwareengineer@gmail.com>. This overrides any tool default that appends attribution trailers. `verify.sh` asserts `core.hooksPath` is set, so a fresh clone can't silently commit unguarded. "claude" as a repo TOPIC remains fine — the ban is on authorship strings, not on honestly naming the API.
12. **Secrets handling** (amended key names — see table above). The session STOPS and asks for each secret when first needed; never invents placeholder values that look real. `.claude/settings.json` denies Claude reads of `./.env` and `./dashboard/.env*` as mechanical backing.
13. **Structured logging to stdout as JSON** (unchanged), plus the run-row insert-first/finalize pattern so early crashes still leave a `started_at` row; if Supabase itself is down, Actions stdout is the second layer.
14. **Pipeline order is persist-then-score** (new; resolves an internal contradiction in the original doc). The original listed `score → persist` yet required degraded runs to "persist with status NEW" and next-run pickup — impossible if dedupe strips DB-resident rows before the scorer. Now: rows are born NEW right after dedupe; the scorer works off a DB query (`status='NEW' AND score_attempts < 6`); each success is a per-row UPDATE to SCORED. "Data capture never depends on the LLM" becomes literally true, paid scoring work survives mid-run crashes, and the degraded-run recovery path is the same code path as a normal run.
15. **Notification semantics, fully specified** (new). Pool: `status='SCORED' AND score >= min_score AND scored_at >= now() - 24h` — DB-wide so crashed-run leftovers self-heal, 24h-bounded because a 3-day-old gig notification is worthless (bidding windows are hours) and must not crowd out today's jobs; older SCORED rows simply never get selected (no sweep, no new status). Order: score DESC, fetched_at DESC; take up to 3; 0 qualifying → heartbeat line instead (`PulseFlow: fetched X · matched Y · new Z · scored S · notified 0`), togglable via config, default on — silence must always mean breakage. Format: ONE webhook message, mrkdwn, per job: linked title, score, reasoning truncated ~140 chars. Ordering: post, then CAS flip (Decision P3: duplicate-over-drop).
16. **`.claude/` is the load-bearing subset** (new; Decision P4). Committed: `settings.json` — permissions only (`allow`: `Bash(pytest:*)`, `Bash(.venv/bin/pytest:*)`, `Bash(uv:*)`, `Bash(python:*)`, `Bash(pnpm build:*)`, `Bash(gh run list:*)`, `Bash(gh run view:*)`, `Bash(gh run watch:*)`; `deny`: `Read(./.env)`, `Read(./dashboard/.env*)`), NO hooks — the owner's global Stop hook already execs `verify.sh`, and a project duplicate would run pytest twice; `gh workflow run`, `git commit/push` deliberately stay prompt-gated (they have real-world side effects). `CLAUDE.md` (~16 lines): spec pointer, stack locks (banned in v1: FastAPI, LangGraph, Inngest, dashboard auth, paid tiers), the four invariants (dedupe-before-scoring; three-status enum is the only idempotency mechanism; LLM failure degrades / infra failure fails red; keywords.json drives filtering), attribution + secrets rules, the three commands, and a feed-status line Phase 1 overwrites. `verify.sh`: dirty-tree early-exit (`git diff --quiet && git diff --cached --quiet && exit 0`), hooksPath assertion, then `.venv/bin/pytest -q`. Cut with reasons: `rules/` (whole instruction surface is one screen), `skills/` (every candidate wraps a one-liner already in CLAUDE.md), `.mcp.json` (a standing service-role credential in every session vs on-demand scripts — worse blast radius for zero gain), `CLAUDE.local.md` (the personal layer already exists at `~/.claude/CLAUDE.md`). `agents/pipeline-debugger.md` is written at Phase 4, when there is production to debug: pull `gh run view --log`, correlate with `workflow_runs` and job statuses, isolate the failing stage, propose the minimal fix.
17. **Scoring prompt is a versioned file** (new; Decision P2), `src/pulseflow/prompts/scoring.md`: profile block (TypeScript/Next.js/Supabase; native Swift iOS — no Android/RN/Flutter; Python AI/agentic — LangGraph, RAG, MCP), band anchors (9–10 direct stack match + clear scope; 7–8 strong match, minor unknowns; 5–6 adjacent skills or vague scope; 3–4 weak fit; 1–2 out of stack or red flags), input = title + HTML-stripped description truncated to 2,000 chars (full text still persisted), and the line: *"Your reasoning is displayed publicly — describe fit factually; do not state rate thresholds or client-filter strategy."* Week-one calibration ritual documented in README: review the score distribution, adjust `min_score` in config.
18. **Feed-death detection is in-pipeline** (new). `fetcher.py` fetches with httpx (30s timeout, status + Content-Type checks) and parses bytes with feedparser; `bozo=1`, non-XML Content-Type, or 0 entries from a non-empty body is recorded as a fetch error in `workflow_runs.errors` and surfaces in the heartbeat as `fetched 0 (feed error)` — a dead feed is visible in Slack within 24h, not discovered months later. (A dead feed still exits 1 per Decision 7 only when ALL feeds fail; a single broken feed among several logs and continues.)
19. **No credential can reach a public surface** (new). `workflow_runs.errors` is world-readable by design (anon SELECT), and httpx exception strings embed request URLs — for the notifier, the URL IS the Slack credential. The store's error sanitizer strips URLs/query strings (`https://\S+` → `[url]`) from every persisted message; notifier errors record only status code + `"slack webhook failed"`. `test_store.py` asserts the webhook URL never appears in a serialized errors payload. `config.py` and logging never print env VALUES (GitHub masks secrets in Actions logs, but Supabase rows have no such protection).
20. **Feed HTML is hostile input** (new). Descriptions are stripped to plain text at ingest (stdlib `html.parser`, no new dependency) — anyone can post a Freelancer job, so raw HTML reaching the dashboard is a stored-XSS vector. The dashboard renders text only (never `dangerouslySetInnerHTML`), shows a ~300-char snippet plus an outbound "view on Freelancer.com" link — which also keeps republication within honest bounds.
21. **Dashboard architecture** (new): latest stable Next.js via create-next-app — the original's "15" read as authored-when-current, per its own Decision 10 rationale ("the current default stack"); pinning a superseded major in a portfolio is a negative signal. Server Components with `export const revalidate = 300` — data changes once a day; 5-minute staleness is fine and polling is overkill. Every query has explicit `.order().limit()` (jobs: last 200; runs: last 90 days) because supabase-js silently truncates at 1,000 rows. Timestamps render server-side in `Asia/Karachi` with an explicit "PKT" label (deterministic — no hydration mismatch; matches the audience of one). "Acceptance stats" means the pipeline funnel (fetched → filtered → new → scored → notified, % of scored ≥ min_score) — computable from existing data, no bid tracking. `error.tsx` + empty states: a paused Supabase project must show "data source unreachable," not a broken portfolio page.
22. **uv + committed lockfile** (new): `uv sync --locked` in CI so the unattended daily cron never silently picks up new dependency versions; hatchling build backend, src layout so `import pulseflow` works; local `uv venv` creates `.venv` so `verify.sh` works unchanged. Alternative (pip, no lockfile) rejected: unpinned deps in an unattended cron is how zero-maintenance projects die.

### Manual-step STOP points, in build order

1. Supabase: create project in browser, run `db/schema.sql` in the SQL editor, copy URL + publishable key + secret key (confirm `sb_publishable_`/`sb_secret_` formats).
2. Anthropic: paste API key when Phase 1 scoring is first wired.
3. Slack: create the incoming webhook, paste the URL.
4. GitHub: add the four repository secrets.
5. Vercel: import `dashboard/` as a project (root directory = `dashboard/`), set the two public env vars.
6. GitHub repo metadata after deploy: About description, topics (python, automation, workflow-orchestration, claude, supabase, github-actions, slack), website → live Vercel URL, social preview. "claude" as a topic is fine; the ban covers authorship strings only.

---

## Out of scope

Locked exclusions. None ship in v1; none may be claimed publicly.

- Multi-tenant anything. No claim of SaaS.
- UI for non-technical users. Configuration is JSON + env vars, stated plainly.
- "Replaces Zapier for any use case." The claim: replaces one specific Zapier-class workflow and demonstrates the pattern.
- Upwork official API integration or authenticated scraping. (Reaffirmed with the source pivot: the API needs partner approval + OAuth. Public feeds only.)
- A second live JobSource implementation. Remotive is documented as the verified fallback candidate (24h delay, salaried job class, attribution terms) — one sentence in ARCHITECTURE.md, no `remotive.py`. The protocol is proven by tests with a fake source.
- Auto-apply or proposal drafting. The system scores and notifies; the human bids.
- LangGraph. A linear pipeline does not need a graph framework; the README says exactly that.
- Inngest, queues, background-job infra. Documented as the scaling path.
- Email, SMS, any channel beyond Slack + dashboard.
- Auth on the dashboard. Read-only public data, RLS write-locked. Supabase Auth magic-link is the documented path if that changes.
- Paid tiers of any service. Free-tier limit hit → scope reduction, never spend.
- Historical backfill. Day one of deployment forward.
- `rules/`, `skills/`, `.mcp.json` under `.claude/` (Decision P4) — revisit when CLAUDE.md exceeds ~60 lines or a multi-step ritual gets typed 3+ times.

---

## Verification

`.claude/verify.sh` (invoked by the owner's global Stop hook; the dirty-tree gate lives HERE because the global hook has none):

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
git diff --quiet && git diff --cached --quiet && exit 0
[ "$(git config core.hooksPath || true)" = ".githooks" ] || { echo "BLOCK: run: git config core.hooksPath .githooks" >&2; exit 2; }
.venv/bin/pytest -q
```

Per-phase acceptance gates. A phase is done only when its gate passes; commit happens at the gate, never before.

**Phase 0 — Scaffold.** `tree` matches the Files section (minus `agents/`, which is Phase 4). `uv run pytest -q` passes (test_config.py already real). `git log -1 --format=fuller` shows exactly one author, no trailers. A test commit containing "claude" in the message is REJECTED by the hook (test once, then amend). LICENSE present.

**Phase 1 — Fetch, filter, score locally.** Feed validation result (Freelancer alive; Upwork 410/403 evidence) logged in `.claude/CLAUDE.md`. `uv run python scripts/run_hunt.py --dry-run` fetches real jobs, filters via keywords.json, prints scored results with reasoning. Mocked tests cover scorer success / retry-then-success / double-failure→NEW, and fetcher fixtures: valid XML, HTML-with-200 (detected as feed error, not silent zero), empty body, missing GUIDs (skip-and-log, URL fallback). STOP honored for ANTHROPIC_API_KEY.

**Phase 2 — Persistence and idempotency.** Schema applied. Back-to-back double run proves idempotency deterministically (a live feed can add jobs between runs, so the gate is set-based, not count-zero): no duplicate GUIDs in `jobs`; second-run `jobs_new` counts only GUIDs absent from run one; no job scored twice (`score_attempts` unchanged for run-one rows). A degraded run's NEW rows get scored by the next run. RLS: publishable key SELECTs; publishable INSERT fails.

**Phase 3 — Slack and dashboard.** Top ≤3 posted in one message: linked title, score, one-line reasoning. Immediate re-run posts nothing (CAS status guard proven). Heartbeat fires on an artificially quiet run. Dashboard live on Vercel with real data, error/empty states render. Secret-leak gate: `grep -rE 'service_role|sb_secret' dashboard/` returns nothing, and `test_store.py`'s sanitizer test passes.

**Phase 4 — Production.** `workflow_dispatch` run green with repo secrets; then 3 consecutive green cron days unattended. Workflow contains: concurrency group, `timeout-minutes: 10`, least-privilege permissions block, self-re-enable step. README: Mermaid diagram, setup, honest caveats (cron delay AND dropped-tick risk, 60-day auto-disable + self-re-enable mitigation, Supabase pause cascade, credits mortality, Freelancer keyword-matching narrowness). `.claude/agents/pipeline-debugger.md` written. Repo metadata per STOP checklist. 60-second demo: trigger dispatch → Actions log → Slack message → dashboard.

**End-to-end check (the sentence that defines done):** From a clean clone with only the four secrets configured, one manual `workflow_dispatch` produces scored jobs in Supabase, a Slack notification, and a dashboard that displays them; an immediate second dispatch notifies no job twice, creates no duplicate GUIDs, and re-scores nothing.
