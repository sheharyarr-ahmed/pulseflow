import Link from "next/link";
import { notFound } from "next/navigation";
import { getClient, hasGivenUp, type Job } from "@/lib/supabase";
import { pkt, snippet } from "@/lib/format";
import Reveal from "@/components/Reveal";
import StatusNotice from "@/components/StatusNotice";

export const revalidate = 300;

function Unreachable() {
  return (
    <StatusNotice>
      Data source unreachable. A paused free-tier database is the usual cause.
    </StatusNotice>
  );
}

const dt = "font-mono text-[11px] uppercase tracking-[0.14em] text-muted";

export default async function JobPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const supabase = getClient();
  if (!supabase) return <Unreachable />;

  const { data, error } = await supabase.from("jobs").select("*").eq("id", id).maybeSingle();
  if (error) return <Unreachable />;
  if (!data) notFound();
  const job = data as Job;

  const statusLabel = hasGivenUp(job) ? "GAVE UP" : job.status;
  const pillTone =
    statusLabel === "NOTIFIED"
      ? "bg-pulse-dim text-pulse-text"
      : statusLabel === "SCORED"
        ? "bg-amber-500/10 text-amber-600 dark:text-amber-400"
        : "bg-zinc-500/10 text-zinc-600 dark:text-zinc-400";
  // The score is why this job got through — it gets the monumental numeral.
  const scoreText =
    job.score != null && job.score >= 7
      ? "text-pulse-text"
      : job.score != null && job.score >= 5
        ? "text-amber-600 dark:text-amber-400"
        : "text-muted";

  return (
    <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-10 md:px-10 md:py-14">
      <div className="grid gap-10 md:grid-cols-[1fr_20rem]">
        <Reveal>
          <Link
            href="/"
            className="font-mono text-xs text-muted transition-colors hover:text-foreground"
          >
            ← overview
          </Link>
          <h1 className="mt-4 text-balance text-2xl font-semibold leading-snug tracking-tight md:text-3xl">
            {job.title ?? "(untitled)"}
          </h1>

          {job.reasoning && (
            <section className="mt-8">
              <h2 className={dt}>Scoring reasoning</h2>
              {/* text-only render — never dangerouslySetInnerHTML (Decision 20) */}
              <div className="mt-3 rounded-xl border border-edge border-l-2 border-l-pulse bg-surface p-6">
                <p className="text-[15px] leading-relaxed">{job.reasoning}</p>
              </div>
            </section>
          )}

          <section className="mt-8">
            <h2 className={dt}>Snippet</h2>
            <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted">
              {snippet(job.description) || "—"}
            </p>
          </section>
        </Reveal>

        <Reveal delay={100} className="md:sticky md:top-20 md:self-start">
          <div className="rounded-xl border border-edge bg-surface p-6">
            <p className={`font-mono text-6xl tabular-nums tracking-tight ${scoreText}`}>
              {job.score ?? "—"}
              <span className="ml-1 text-base text-muted">/10</span>
            </p>

            <dl className="mt-6 grid grid-cols-[5.5rem_1fr] items-baseline gap-y-3 text-sm">
              <dt className={dt}>status</dt>
              <dd>
                <span
                  className={`inline-flex items-center rounded-full px-2.5 py-0.5 font-mono text-[11px] uppercase tracking-wide ${pillTone}`}
                >
                  {statusLabel}
                </span>
              </dd>
              <dt className={dt}>source</dt>
              <dd className="font-mono">{job.source ?? "—"}</dd>
              <dt className={dt}>fetched</dt>
              <dd className="font-mono tabular-nums">{pkt(job.fetched_at)}</dd>
              <dt className={dt}>scored</dt>
              <dd className="font-mono tabular-nums">{pkt(job.scored_at)}</dd>
              <dt className={dt}>notified</dt>
              <dd className="font-mono tabular-nums">{pkt(job.notified_at)}</dd>
            </dl>

            {job.url && (
              <a
                href={job.url}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-6 block rounded-lg bg-pulse px-4 py-2.5 text-center text-sm font-medium text-emerald-950 transition-opacity hover:opacity-90"
              >
                View on Freelancer.com ↗
              </a>
            )}
          </div>
        </Reveal>
      </div>
    </main>
  );
}
