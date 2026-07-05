import Link from "next/link";
import { getClient, HEARTBEAT_FRESH_MS } from "@/lib/supabase";
import { pkt } from "@/lib/format";
import NavLink from "./NavLink";
import ThemeToggle from "./ThemeToggle";

async function lastHeartbeat(): Promise<string | null> {
  const supabase = getClient();
  if (!supabase) return null;
  const { data, error } = await supabase
    .from("workflow_runs")
    .select("started_at")
    .order("started_at", { ascending: false })
    .limit(1)
    .maybeSingle();
  if (error || !data) return null;
  return data.started_at as string;
}

function StatusDot({ startedAt }: { startedAt: string | null }) {
  // Real status, not decoration: emerald + breathing while the daily run is
  // fresh, amber once it's overdue, zinc when the data source is unreachable.
  const fresh =
    // eslint-disable-next-line react-hooks/purity -- server component under 5-min ISR: freshness re-evaluates per revalidation by design
    startedAt !== null && Date.now() - Date.parse(startedAt) < HEARTBEAT_FRESH_MS;
  const dot = !startedAt
    ? "bg-zinc-400 dark:bg-zinc-600"
    : fresh
      ? "dot-live bg-pulse"
      : "bg-amber-500";
  return (
    <span className="flex items-center gap-2" title="Last pipeline run">
      <span aria-hidden className={`size-2 shrink-0 rounded-full ${dot}`} />
      <span className="hidden font-mono text-[11px] text-muted md:inline">
        {startedAt ? `last run ${pkt(startedAt)}` : "—"}
      </span>
    </span>
  );
}

export default async function SiteNav() {
  const startedAt = await lastHeartbeat();

  return (
    <nav className="sticky top-0 z-40 border-b border-edge/60 bg-background/80 backdrop-blur-md">
      <div className="mx-auto flex h-14 max-w-6xl items-center gap-6 px-6 md:px-10">
        <Link href="/" className="flex items-center gap-2.5">
          {/* eslint-disable-next-line @next/next/no-img-element -- static brand SVG, no optimization needed */}
          <img
            src="/brand/mark-light.svg"
            alt=""
            className="size-5 dark:hidden"
          />
          {/* eslint-disable-next-line @next/next/no-img-element -- static brand SVG, no optimization needed */}
          <img
            src="/brand/mark-dark.svg"
            alt=""
            className="hidden size-5 dark:block"
          />
          <span className="text-[15px] font-semibold tracking-[-0.02em]">
            PulseFlow
          </span>
        </Link>

        <div className="flex items-center gap-5 sm:gap-6">
          <NavLink href="/">Overview</NavLink>
          <NavLink href="/runs">Runs</NavLink>
        </div>

        <div className="ml-auto flex items-center gap-4">
          <StatusDot startedAt={startedAt} />
          <ThemeToggle />
        </div>
      </div>
    </nav>
  );
}
