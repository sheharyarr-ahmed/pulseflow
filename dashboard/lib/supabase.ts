// Publishable-key server client, read-only via RLS. The secret key never lives
// under dashboard/ — all writes happen in the GitHub Actions pipeline.
// Every query is explicit .order().limit() because supabase-js silently
// truncates at 1000 rows.

import { createClient } from "@supabase/supabase-js";

const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
const key = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;

export type JobStatus = "NEW" | "SCORED" | "NOTIFIED";

export type Job = {
  id: string;
  guid: string;
  source: string | null;
  url: string | null;
  title: string | null;
  description: string | null;
  score: number | null;
  reasoning: string | null;
  status: JobStatus;
  score_attempts: number;
  fetched_at: string;
  scored_at: string | null;
  notified_at: string | null;
};

export type WorkflowRun = {
  id: string;
  started_at: string;
  finished_at: string | null;
  jobs_fetched: number | null;
  jobs_filtered: number | null;
  jobs_new: number | null;
  jobs_scored: number | null;
  jobs_notified: number | null;
  errors: { stage: string; type: string; message: string }[] | null;
  duration_seconds: number | null;
};

// Returns null when env is unset so pages can render the "unreachable" state
// instead of failing the build (a paused project is not a broken portfolio).
export function getClient() {
  if (!url || !key) return null;
  return createClient(url, key, { auth: { persistSession: false } });
}

// A job that scored but was never picked up again is "gave up" once it hits the
// lifetime attempts cap (SPEC.md: derived, not a stored status).
export const GAVE_UP_ATTEMPTS = 6;

export function hasGivenUp(job: Pick<Job, "status" | "score_attempts">): boolean {
  return job.status === "NEW" && job.score_attempts >= GAVE_UP_ATTEMPTS;
}
