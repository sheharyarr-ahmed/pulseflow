# PulseFlow

Spec: SPEC.md is authoritative; this file is the working summary.

**Stack locks (banned in v1):** FastAPI, LangGraph, Inngest, dashboard auth, paid tiers.

**Invariants:**
1. Dedupe before scoring — the LLM never re-scores a seen GUID.
2. The three-status enum (NEW → SCORED → NOTIFIED) is the only idempotency mechanism.
3. LLM failure degrades (exit 0, retry next run); fetch/Supabase failure fails red (exit 1).
4. config/keywords.json drives all filtering — nothing hardcoded.

**Attribution:** single author Sheharyar Ahmed; commit-msg hook rejects attribution strings; no trailers. **Secrets:** never fabricate; STOP and ask; .env is read-denied.

**Commands:** `uv run pytest -q` · `uv run python scripts/run_hunt.py --dry-run` · `pnpm build` (in dashboard/).

**Phase 0 tree-gate interpretation:** every SPEC.md-listed path exists; create-next-app extras and tests/fixtures/ are allowed additions.

Feed status (validated live 2026-07-04): Freelancer keyword RSS alive — `rss.xml?keyword=react` → 200 `text/xml`, 20 items, stable `<guid isPermaLink="false">Freelancer_project_NNNN</guid>`. Upwork RSS dead — `/ab/feed/jobs/rss` → 410, `/nx/search/jobs/rss` → 403 (Cloudflare).
