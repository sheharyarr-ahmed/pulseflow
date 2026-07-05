import { getClient, type WorkflowRun } from "@/lib/supabase";
import { pkt } from "@/lib/format";
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

// Dense-ledger hierarchy: zeros and nulls fade out so non-zero values carry
// the row; "notified" is the signal column and gets the emerald text pair.
function Num({ v, tone = "default" }: { v: number | null; tone?: "default" | "pulse" }) {
  if (v == null || v === 0)
    return <span className="text-zinc-300 dark:text-zinc-600">{v ?? "—"}</span>;
  if (tone === "pulse")
    return <span className="font-medium text-pulse-text">{v}</span>;
  return <>{v}</>;
}

export default async function RunsPage() {
  const supabase = getClient();
  if (!supabase) return <Unreachable />;

  // Last 90 days, explicit order + limit (supabase-js truncates at 1000).
  // eslint-disable-next-line react-hooks/purity -- server component under 5-min ISR: cutoff re-evaluates per revalidation by design
  const cutoff = new Date(Date.now() - 90 * 24 * 60 * 60 * 1000).toISOString();
  const { data, error } = await supabase
    .from("workflow_runs")
    .select("*")
    .gte("started_at", cutoff)
    .order("started_at", { ascending: false })
    .limit(1000);

  if (error) return <Unreachable />;
  const runs = (data ?? []) as WorkflowRun[];

  const th =
    "py-3 pr-4 text-left font-mono text-[11px] font-medium uppercase tracking-[0.14em] text-muted md:sticky md:top-14 bg-surface";

  return (
    <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-10 md:px-10 md:py-14">
      <Reveal>
        <p className="font-mono text-xs uppercase tracking-[0.14em] text-pulse-text">
          Run log · 90 days
        </p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight">
          Workflow runs
        </h1>
        <p className="mt-2 font-mono text-xs text-muted">{runs.length} runs</p>
      </Reveal>

      {runs.length === 0 ? (
        <div className="mt-8 rounded-xl border border-edge bg-surface p-6 md:p-8">
          <p className="text-sm text-muted">No runs recorded yet.</p>
        </div>
      ) : (
        <Reveal
          delay={100}
          className="mt-8 overflow-x-auto rounded-xl border border-edge bg-surface md:overflow-visible"
        >
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-edge">
                <th className={`${th} w-8 pl-5`}>
                  <span className="sr-only">status</span>
                </th>
                <th className={th}>started (PKT)</th>
                <th className={th}>fetched</th>
                <th className={th}>matched</th>
                <th className={th}>new</th>
                <th className={th}>scored</th>
                <th className={th}>notified</th>
                <th className={th}>errors</th>
                <th className={th}>secs</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((r, i) => {
                const errs = r.errors?.length ?? 0;
                return (
                  <tr
                    key={r.id}
                    className="border-b border-edge/60 transition-colors last:border-0 hover:bg-pulse-dim"
                  >
                    <td className="py-2.5 pl-5 pr-4">
                      <span
                        aria-hidden
                        className={`block size-1.5 rounded-full ${
                          errs
                            ? "bg-red-500"
                            : `bg-pulse ${i === 0 ? "dot-live" : ""}`
                        }`}
                      />
                    </td>
                    <td className="whitespace-nowrap py-2.5 pr-4 font-mono tabular-nums text-muted">
                      {pkt(r.started_at)}
                    </td>
                    <td className="py-2.5 pr-4 font-mono tabular-nums">
                      <Num v={r.jobs_fetched} />
                    </td>
                    <td className="py-2.5 pr-4 font-mono tabular-nums">
                      <Num v={r.jobs_filtered} />
                    </td>
                    <td className="py-2.5 pr-4 font-mono tabular-nums">
                      <Num v={r.jobs_new} />
                    </td>
                    <td className="py-2.5 pr-4 font-mono tabular-nums">
                      <Num v={r.jobs_scored} />
                    </td>
                    <td className="py-2.5 pr-4 font-mono tabular-nums">
                      <Num v={r.jobs_notified} tone="pulse" />
                    </td>
                    <td
                      className={`py-2.5 pr-4 font-mono tabular-nums ${
                        errs
                          ? "font-semibold text-red-600 dark:text-red-400"
                          : "text-zinc-300 dark:text-zinc-600"
                      }`}
                    >
                      {errs}
                    </td>
                    <td className="py-2.5 pr-4 font-mono tabular-nums text-muted">
                      {r.duration_seconds != null
                        ? r.duration_seconds.toFixed(1)
                        : "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </Reveal>
      )}
    </main>
  );
}
