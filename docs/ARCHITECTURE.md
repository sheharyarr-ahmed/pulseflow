# PulseFlow architecture

_Sections filled in as the phases land; final at Phase 4._

## Pipeline

Fetch (Freelancer.com keyword RSS) → filter (keywords.json) → dedupe (GUID) → persist NEW → score (claude-haiku-4-5) → notify (Slack) → workflow_runs row.

## Honest limitations

_Phase 4: Actions cron delay + dropped ticks, 60-day auto-disable + self-re-enable, Supabase pause cascade, credits mortality, Freelancer keyword narrowness. Remotive is the documented (not built) fallback JobSource._

## Scaling path

_Phase 4: what changes if this ever needs queues/multi-tenant (Inngest et al. — deliberately out of v1 scope)._
