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

// Score → tinted ring chip. Text colors use the contrast-safe pair per theme
// (darker emerald/amber on light, lighter on dark).
export function scoreTone(score: number | null): string {
  if (score != null && score >= 7)
    return "bg-emerald-500/10 text-emerald-600 ring-1 ring-inset ring-emerald-500/25 dark:text-emerald-400 dark:ring-emerald-400/25";
  if (score != null && score >= 5)
    return "bg-amber-500/10 text-amber-600 ring-1 ring-inset ring-amber-500/25 dark:text-amber-400 dark:ring-amber-400/25";
  return "bg-zinc-500/10 text-zinc-600 ring-1 ring-inset ring-zinc-500/25 dark:text-zinc-400 dark:ring-zinc-400/25";
}
