import Link from "next/link";
import { notFound } from "next/navigation";
import { getClient, hasGivenUp, type Job } from "@/lib/supabase";
import { pkt, snippet, scoreTone } from "@/lib/format";

export const revalidate = 300;

function Unreachable() {
  return (
    <main className="mx-auto max-w-2xl p-8">
      <h1 className="text-2xl font-semibold">Job</h1>
      <p className="mt-4 rounded-md border border-amber-300 bg-amber-50 p-4 text-sm dark:border-amber-800 dark:bg-amber-950">
        Data source unreachable. A paused free-tier database is the usual cause.
      </p>
    </main>
  );
}

export default async function JobPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const supabase = getClient();
  if (!supabase) return <Unreachable />;

  const { data, error } = await supabase.from("jobs").select("*").eq("id", id).maybeSingle();
  if (error) return <Unreachable />;
  if (!data) notFound();
  const job = data as Job;

  const statusLabel = hasGivenUp(job) ? "GAVE UP" : job.status;

  return (
    <main className="mx-auto max-w-2xl p-8">
      <Link href="/" className="text-sm underline underline-offset-4">
        ← home
      </Link>

      <div className="mt-4 flex items-start gap-3">
        <span
          className={`mt-1 inline-flex h-8 w-11 shrink-0 items-center justify-center rounded text-sm font-semibold tabular-nums ${scoreTone(
            job.score,
          )}`}
        >
          {job.score ?? "—"}
        </span>
        <h1 className="text-xl font-semibold leading-snug">{job.title ?? "(untitled)"}</h1>
      </div>

      <dl className="mt-6 grid grid-cols-[7rem_1fr] gap-y-2 text-sm">
        <dt className="text-zinc-500">status</dt>
        <dd className="tabular-nums">{statusLabel}</dd>
        <dt className="text-zinc-500">source</dt>
        <dd>{job.source ?? "—"}</dd>
        <dt className="text-zinc-500">fetched</dt>
        <dd className="tabular-nums">{pkt(job.fetched_at)}</dd>
        <dt className="text-zinc-500">scored</dt>
        <dd className="tabular-nums">{pkt(job.scored_at)}</dd>
        <dt className="text-zinc-500">notified</dt>
        <dd className="tabular-nums">{pkt(job.notified_at)}</dd>
      </dl>

      {job.reasoning && (
        <section className="mt-6">
          <h2 className="text-sm font-medium text-zinc-500">Scoring reasoning</h2>
          {/* text-only render — never dangerouslySetInnerHTML (Decision 20) */}
          <p className="mt-2 text-sm leading-relaxed">{job.reasoning}</p>
        </section>
      )}

      <section className="mt-6">
        <h2 className="text-sm font-medium text-zinc-500">Snippet</h2>
        <p className="mt-2 text-sm leading-relaxed text-zinc-600 dark:text-zinc-300">
          {snippet(job.description) || "—"}
        </p>
      </section>

      {job.url && (
        <a
          href={job.url}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-6 inline-block text-sm underline underline-offset-4"
        >
          View on Freelancer.com →
        </a>
      )}
    </main>
  );
}
