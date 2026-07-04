import Link from "next/link";
import { getClient, type Job, type WorkflowRun } from "@/lib/supabase";
import { pkt, scoreTone } from "@/lib/format";

export const revalidate = 300; // data changes once a day; 5-minute ISR is plenty

function Unreachable() {
  return (
    <main className="mx-auto max-w-4xl p-8">
      <h1 className="text-2xl font-semibold">PulseFlow</h1>
      <p className="mt-4 rounded-md border border-amber-300 bg-amber-50 p-4 text-sm dark:border-amber-800 dark:bg-amber-950">
        Data source unreachable. A paused free-tier database is the usual cause — the
        pipeline itself may still be running fine.
      </p>
    </main>
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

  return (
    <main className="mx-auto max-w-4xl p-8">
      <header className="flex items-baseline justify-between">
        <h1 className="text-2xl font-semibold">PulseFlow</h1>
        <Link href="/runs" className="text-sm underline underline-offset-4">
          run log →
        </Link>
      </header>
      <p className="mt-1 text-sm text-zinc-500">
        Daily freelance-market job hunt · scored by claude-haiku-4-5
      </p>

      <section className="mt-8">
        <h2 className="text-sm font-medium text-zinc-500">
          Pipeline funnel · last {runs.length} runs
        </h2>
        <div className="mt-3 space-y-2">
          {funnel.map((f) => (
            <div key={f.label} className="flex items-center gap-3">
              <span className="w-20 text-sm tabular-nums text-zinc-500">{f.label}</span>
              <div className="h-5 flex-1 overflow-hidden rounded bg-zinc-100 dark:bg-zinc-800">
                <div
                  className="h-full rounded bg-zinc-400 dark:bg-zinc-500"
                  style={{ width: `${(f.value / max) * 100}%` }}
                />
              </div>
              <span className="w-12 text-right text-sm tabular-nums">{f.value}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="mt-10">
        <h2 className="text-sm font-medium text-zinc-500">Recently notified</h2>
        {jobs.length === 0 ? (
          <p className="mt-3 text-sm text-zinc-500">No notified jobs yet.</p>
        ) : (
          <ul className="mt-3 divide-y divide-zinc-100 dark:divide-zinc-800">
            {jobs.map((j) => (
              <li key={j.id} className="flex items-center gap-3 py-2">
                <span
                  className={`inline-flex h-6 w-9 shrink-0 items-center justify-center rounded text-xs font-semibold tabular-nums ${scoreTone(
                    j.score,
                  )}`}
                >
                  {j.score ?? "—"}
                </span>
                <Link
                  href={`/jobs/${j.id}`}
                  className="flex-1 truncate text-sm underline-offset-4 hover:underline"
                >
                  {j.title ?? "(untitled)"}
                </Link>
                <span className="shrink-0 text-xs tabular-nums text-zinc-400">
                  {pkt(j.notified_at)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
