// Server-side, deterministic formatting. Timestamps render in Asia/Karachi with
// an explicit "PKT" label — no DST in Pakistan, so no hydration mismatch and no
// client re-formatting (SPEC.md Decision 21).

const PKT = new Intl.DateTimeFormat("en-GB", {
  timeZone: "Asia/Karachi",
  year: "numeric",
  month: "short",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

export function pkt(iso: string | null): string {
  if (!iso) return "—";
  return `${PKT.format(new Date(iso))} PKT`;
}

export function snippet(text: string | null, max = 300): string {
  if (!text) return "";
  const collapsed = text.replace(/\s+/g, " ").trim();
  return collapsed.length <= max ? collapsed : collapsed.slice(0, max - 1) + "…";
}

// Score → tint. Neutral, works in light and dark.
export function scoreTone(score: number | null): string {
  if (score == null) return "bg-zinc-200 text-zinc-700 dark:bg-zinc-700 dark:text-zinc-200";
  if (score >= 7) return "bg-emerald-200 text-emerald-900 dark:bg-emerald-900 dark:text-emerald-100";
  if (score >= 5) return "bg-amber-200 text-amber-900 dark:bg-amber-900 dark:text-amber-100";
  return "bg-zinc-200 text-zinc-700 dark:bg-zinc-700 dark:text-zinc-200";
}
