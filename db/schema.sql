-- PulseFlow schema. Run once in the Supabase SQL editor (Phase 2 STOP point).
-- Exactly three statuses; staleness and give-up states are derived, not stored.

create table if not exists jobs (
    id             uuid primary key default gen_random_uuid(),
    guid           text unique not null,
    source         text not null default 'freelancer',
    url            text,
    title          text,
    description    text,                     -- plain text: HTML stripped at ingest
    score          smallint     check (score between 1 and 10),
    reasoning      text,
    status         text not null check (status in ('NEW', 'SCORED', 'NOTIFIED')),
    score_attempts smallint not null default 0,
    fetched_at     timestamptz not null,
    scored_at      timestamptz,
    notified_at    timestamptz
);

create index if not exists jobs_guid_idx on jobs (guid);
create index if not exists jobs_status_idx on jobs (status);

create table if not exists workflow_runs (
    id               uuid primary key default gen_random_uuid(),
    started_at       timestamptz not null,
    finished_at      timestamptz,
    jobs_fetched     int,
    jobs_filtered    int,
    jobs_new         int,
    jobs_scored      int,
    jobs_notified    int,
    errors           jsonb,                  -- [{stage, type, message}] — messages sanitized (Decision 19)
    duration_seconds numeric
);

-- RLS: publishable (anon) role may only SELECT. All writes go through the
-- secret key (GitHub Actions only) which bypasses RLS.
alter table jobs enable row level security;
alter table workflow_runs enable row level security;

create policy jobs_public_read on jobs
    for select to anon using (true);

create policy workflow_runs_public_read on workflow_runs
    for select to anon using (true);
