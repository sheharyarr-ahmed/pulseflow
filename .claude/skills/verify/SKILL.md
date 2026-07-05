---
name: verify
description: Runtime verification recipe for PulseFlow — how to build, launch, and drive the dashboard (and pipeline) to observe changes working.
---

# PulseFlow verification recipe

## Dashboard (Next.js, dashboard/)

**Verify against the production build, not `next dev`.** The Turbopack dev
cache has served stale CSS from a previous session even after a server
restart (observed 2026-07-05: old globals.css with rules that no longer
existed on disk). `next build` + `next start` has no such cache and is closer
to what Vercel serves.

```bash
cd dashboard
pnpm build                              # must be green
pnpm exec next start -p 3457 &          # .env.local is picked up automatically
```

Drive it with Playwright from the npx cache (no install needed):

- require `playwright-core` from `~/.npm/_npx/*/node_modules/playwright-core`
- launch chromium with `executablePath` pointing at
  `~/Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-mac-arm64/chrome-headless-shell`
  (the npx-cached playwright may expect a newer browser build than what is
  installed — pinning executablePath sidesteps the mismatch).

Flows worth driving: `/` (hero EKG draw, funnel bar growth after scrolling,
notified list), `/runs` (cell hierarchy, status dots), a real `/jobs/<id>`
(grab the first link from the home list), theme toggle + reload persistence
(`localStorage.theme`), an unknown-but-valid UUID (→ designed 404), a
malformed job id (Supabase errors on invalid uuid → Unreachable state, HTTP
200), `reducedMotion: "reduce"` and `javaScriptEnabled: false` contexts
(all content must be visible — reveal styles gate on `html.js`).

Gotchas:
- Screenshots taken right after clicking the theme toggle catch
  `transition-colors` mid-flight and make table cells look unreadable —
  probe `getComputedStyle(...).color` for ground truth, or wait ~300ms.
- Scroll through the page before full-page screenshots or below-fold
  `[data-reveal]` sections are still hidden.
- `.env` / `.env.local` are read-denied by policy — never cat or ls them;
  the server loads them on its own. No env → pages render the designed
  "unreachable" state, which is itself a flow worth screenshotting.

## Pipeline (Python, root)

`uv run python scripts/run_hunt.py --dry-run` exercises fetch/filter/dedupe
without writes. `uv run pytest -q` is CI's job, not verification.
