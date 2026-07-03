# PulseFlow

Code-first workflow orchestration that replaces one Zapier-class workflow: a daily freelance-market job hunt. A GitHub Actions cron fetches new Freelancer.com job postings, filters them against a configurable keyword list, scores each 1–10 with `claude-haiku-4-5`, and posts the top matches to Slack — with a public dashboard for run history and scores.

> Status: scaffolding (Phase 0). See [SPEC.md](SPEC.md) for the full specification.

## Architecture

_To be completed at Phase 4: Mermaid pipeline diagram, component overview._

## Setup

_To be completed at Phase 4: Supabase schema, secrets, GitHub Actions, Vercel deploy._

## Honest caveats

_To be completed at Phase 4: Actions cron delay and dropped-tick risk, 60-day auto-disable and the self-re-enable mitigation, Supabase free-tier pause cascade, API credits mortality, Freelancer keyword-matching narrowness._

## License

MIT © Sheharyar Ahmed
