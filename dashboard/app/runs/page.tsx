import Link from "next/link";
import { getClient, type WorkflowRun } from "@/lib/supabase";
import { pkt } from "@/lib/format";

export const revalidate = 300;

function Unreachable() {
  return (
    <main className="mx-auto max-w-5xl p-8">
      <h1 className="text-2xl font-semibold">Workflow runs</h1>
      <p className="mt-4 rounded-md border border-amber-300 bg-amber-50 p-4 text-sm dark:border-amber-800 dark:bg-amber-950">
        Data source unreachable. A paused free-tier database is the usual cause.
      </p>
    </main>
  );
}

export default async function RunsPage() {
  const supabase = getClient();
  if (!supabase) return <Unreachable />;

  // Last 90 days, explicit order + limit (supabase-js truncates at 1000).
  const cutoff = new Date(Date.now() - 90 * 24 * 60 * 60 * 1000).toISOString();
  const { data, error } = await supabase
    .from("workflow_runs")
    .select("*")
    .gte("started_at", cutoff)
    .order("started_at", { ascending: false })
    .limit(1000);

  if (error) return <Unreachable />;
  const runs = (data ?? []) as WorkflowRun[];

  return (
    <main className="mx-auto max-w-5xl p-8">
      <header className="flex items-baseline justify-between">
        <h1 className="text-2xl font-semibold">Workflow runs</h1>
        <Link href="/" className="text-sm underline underline-offset-4">
          ← home
        </Link>
      </header>
      <p className="mt-1 text-sm text-zinc-500">Last 90 days · {runs.length} runs</p>

      {runs.length === 0 ? (
        <p className="mt-6 text-sm text-zinc-500">No runs recorded yet.</p>
      ) : (
        <div className="mt-6 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-200 text-left text-xs text-zinc-500 dark:border-zinc-700">
                <th className="py-2 pr-4 font-medium">started (PKT)</th>
                <th className="py-2 pr-4 font-medium tabular-nums">fetched</th>
                <th className="py-2 pr-4 font-medium tabular-nums">matched</th>
                <th className="py-2 pr-4 font-medium tabular-nums">new</th>
                <th className="py-2 pr-4 font-medium tabular-nums">scored</th>
                <th className="py-2 pr-4 font-medium tabular-nums">notified</th>
                <th className="py-2 pr-4 font-medium tabular-nums">errors</th>
                <th className="py-2 pr-4 font-medium tabular-nums">secs</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((r) => {
                const errs = r.errors?.length ?? 0;
                return (
                  <tr key={r.id} className="border-b border-zinc-100 dark:border-zinc-800">
                    <td className="py-2 pr-4 whitespace-nowrap tabular-nums">{pkt(r.started_at)}</td>
                    <td className="py-2 pr-4 tabular-nums">{r.jobs_fetched ?? "—"}</td>
                    <td className="py-2 pr-4 tabular-nums">{r.jobs_filtered ?? "—"}</td>
                    <td className="py-2 pr-4 tabular-nums">{r.jobs_new ?? "—"}</td>
                    <td className="py-2 pr-4 tabular-nums">{r.jobs_scored ?? "—"}</td>
                    <td className="py-2 pr-4 tabular-nums">{r.jobs_notified ?? "—"}</td>
                    <td
                      className={`py-2 pr-4 tabular-nums ${
                        errs ? "font-semibold text-red-600 dark:text-red-400" : "text-zinc-400"
                      }`}
                    >
                      {errs}
                    </td>
                    <td className="py-2 pr-4 tabular-nums text-zinc-400">
                      {r.duration_seconds != null ? r.duration_seconds.toFixed(1) : "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}
