import { scoreTone } from "@/lib/format";

export default function ScoreChip({ score }: { score: number | null }) {
  return (
    <span
      className={`inline-flex h-6 w-9 shrink-0 items-center justify-center rounded-md font-mono text-xs font-semibold tabular-nums ${scoreTone(score)}`}
    >
      {score ?? "—"}
    </span>
  );
}
