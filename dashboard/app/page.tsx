import Link from "next/link";
import {
  getClient,
  HEARTBEAT_FRESH_MS,
  type Job,
  type WorkflowRun,
} from "@/lib/supabase";
import { pkt } from "@/lib/format";
import PulseLine from "@/components/PulseLine";
import Reveal from "@/components/Reveal";
import ScoreChip from "@/components/ScoreChip";
import StatCard from "@/components/StatCard";
import StatusNotice from "@/components/StatusNotice";

export const revalidate = 300; // data changes once a day; 5-minute ISR is plenty

function Unreachable() {
  return (
    <StatusNotice>
      Data source unreachable. A paused free-tier database is the usual cause —
      the pipeline itself may still be running fine.
    </StatusNotice>
  );
}

export default async function Home() {
  const supabase = getClient();
  if (!supabase) return <Unreachable />;

  const [runsRes, jobsRes] = await Promise.all([
    supabase
      .from("workflow_runs")
      .select("*")
      .order("started_at", { ascending: false })
      .limit(30),
    supabase
      .from("jobs")
      .select("*")
      .eq("status", "NOTIFIED")
      .order("notified_at", { ascending: false })
      .limit(50),
  ]);

  if (runsRes.error || jobsRes.error) return <Unreachable />;

  const runs = (runsRes.data ?? []) as WorkflowRun[];
  const jobs = (jobsRes.data ?? []) as Job[];

  // Funnel: sum across the recent runs shown.
  const sum = (k: keyof WorkflowRun) =>
    runs.reduce((n, r) => n + (typeof r[k] === "number" ? (r[k] as number) : 0), 0);
  const funnel = [
    { label: "fetched", value: sum("jobs_fetched") },
    { label: "matched", value: sum("jobs_filtered") },
    { label: "new", value: sum("jobs_new") },
    { label: "scored", value: sum("jobs_scored") },
    { label: "notified", value: sum("jobs_notified") },
  ];
  const max = Math.max(1, ...funnel.map((f) => f.value));

  // Vitals, derived from the same 30 runs — no extra queries.
  const durations = runs
    .map((r) => r.duration_seconds)
    .filter((d): d is number => d != null);
  const avgDuration = durations.length
    ? `${(durations.reduce((a, b) => a + b, 0) / durations.length).toFixed(1)}s`
    : "—";
  const latest = runs[0]?.started_at ?? null;
  const fresh =
    // eslint-disable-next-line react-hooks/purity -- server component under 5-min ISR: freshness re-evaluates per revalidation by design
    latest !== null && Date.now() - Date.parse(latest) < HEARTBEAT_FRESH_MS;
  const lineState = runs.length === 0 ? "flat" : fresh ? "live" : "warn";

  return (
    <main className="flex-1">
      {/* Hero */}
      <section className="relative overflow-hidden">
        <div aria-hidden className="hero-glow pointer-events-none absolute inset-0" />
        <div className="relative mx-auto max-w-6xl px-6 pt-16 pb-10 md:px-10 md:pt-24 md:pb-14">
          <Reveal>
            <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-pulse-text">
              Daily heartbeat · Autonomous pipeline
            </p>
            <h1 className="mt-4 max-w-3xl text-balance text-5xl font-semibold tracking-[-0.04em] md:text-6xl">
              A daily heartbeat for the job hunt.
            </h1>
            <p className="mt-5 max-w-xl text-lg text-muted">
              Fetches new Freelancer projects, dedupes, scores them with
              claude-haiku-4-5, and posts the best to Slack — every morning,
              unattended.
            </p>
          </Reveal>
          <Reveal delay={100} className="mt-8 flex flex-wrap items-center gap-4">
            <Link
              href="/runs"
              className="rounded-lg bg-foreground px-5 py-2.5 text-sm font-medium text-background transition-opacity hover:opacity-85"
            >
              View runs
            </Link>
            <a
              href="#pipeline"
              className="rounded-lg border border-edge px-5 py-2.5 text-sm font-medium transition-colors hover:border-pulse/40"
            >
              How it works
            </a>
            <span className="font-mono text-xs text-muted">
              last heartbeat: {pkt(latest)}
            </span>
          </Reveal>
          <PulseLine state={lineState} className="mt-12" />
        </div>
      </section>

      {/* Vitals */}
      <section className="mx-auto max-w-6xl px-6 pb-14 md:px-10 md:pb-20">
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <StatCard label="Runs tracked" value={String(runs.length)} />
          <StatCard label="Jobs screened" value={String(funnel[0].value)} delay={75} />
          <StatCard
            label="Jobs notified"
            value={String(funnel[4].value)}
            tone="pulse"
            delay={150}
          />
          <StatCard label="Avg run duration" value={avgDuration} delay={225} />
        </div>
      </section>

      {/* Funnel */}
      <section
        id="pipeline"
        className="mx-auto max-w-6xl scroll-mt-20 px-6 pb-14 md:px-10 md:pb-20"
      >
        <Reveal>
          <p className="font-mono text-xs uppercase tracking-[0.14em] text-pulse-text">
            01 — Pipeline
          </p>
          <h2 className="mt-3 text-2xl font-semibold tracking-tight md:text-3xl">
            Fetched to notified
          </h2>
          <p className="mt-2 max-w-xl text-sm text-muted">
            Totals across the last {runs.length} runs. Jobs are deduped before
            scoring — the model never re-scores a seen posting.
          </p>
        </Reveal>
        <Reveal
          delay={100}
          className="mt-8 space-y-4 rounded-xl border border-edge bg-surface p-6 md:p-8"
        >
          {funnel.map((f, i) => (
            <div key={f.label} className="flex items-center gap-4">
              <span className="w-20 shrink-0 font-mono text-xs text-muted">
                {f.label}
              </span>
              <div className="h-9 flex-1 overflow-hidden rounded-md bg-zinc-100 dark:bg-zinc-800/60">
                <div
                  className={`funnel-fill h-full rounded-md ${
                    f.label === "notified"
                      ? "bg-pulse"
                      : "bg-zinc-300 dark:bg-zinc-700"
                  }`}
                  style={
                    {
                      // max() keeps small non-zero stages (e.g. 1 of 431
                      // notified) visible as a nub instead of a 2px sliver
                      width:
                        f.value > 0
                          ? `max(${(f.value / max) * 100}%, 0.75rem)`
                          : "0",
                      "--fill-delay": `${i * 100}ms`,
                    } as React.CSSProperties
                  }
                />
              </div>
              <span className="w-14 shrink-0 text-right font-mono text-sm tabular-nums">
                {f.value}
              </span>
            </div>
          ))}
        </Reveal>
      </section>

      {/* Recently notified */}
      <section className="mx-auto max-w-6xl px-6 pb-20 md:px-10 md:pb-24">
        <Reveal>
          <p className="font-mono text-xs uppercase tracking-[0.14em] text-pulse-text">
            02 — Signal
          </p>
          <h2 className="mt-3 text-2xl font-semibold tracking-tight md:text-3xl">
            Recently notified
          </h2>
          <p className="mt-2 max-w-xl text-sm text-muted">
            The last {jobs.length} jobs that cleared the score threshold and
            went to Slack.
          </p>
        </Reveal>
        {jobs.length === 0 ? (
          <div className="mt-8 rounded-xl border border-edge bg-surface p-6 md:p-8">
            <PulseLine state="flat" className="max-w-sm" />
            <p className="mt-4 text-sm text-muted">
              No notified jobs yet — the pipeline is warming up.
            </p>
          </div>
        ) : (
          <ul className="mt-8 divide-y divide-edge overflow-hidden rounded-xl border border-edge bg-surface">
            {jobs.map((j, i) => {
              const row = (
                <Link
                  href={`/jobs/${j.id}`}
                  className="flex items-center gap-4 px-5 py-3.5 transition-[background-color,box-shadow] hover:bg-pulse-dim hover:shadow-[inset_2px_0_0_var(--color-pulse)]"
                >
                  <ScoreChip score={j.score} />
                  <span className="flex-1 truncate text-sm font-medium">
                    {j.title ?? "(untitled)"}
                  </span>
                  <span className="shrink-0 font-mono text-xs tabular-nums text-muted">
                    {pkt(j.notified_at)}
                  </span>
                </Link>
              );
              return i < 12 ? (
                <Reveal key={j.id} as="li" delay={Math.min(i * 50, 400)}>
                  {row}
                </Reveal>
              ) : (
                <li key={j.id}>{row}</li>
              );
            })}
          </ul>
        )}
      </section>
    </main>
  );
}
