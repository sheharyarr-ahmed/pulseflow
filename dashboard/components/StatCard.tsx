import Reveal from "./Reveal";

export default function StatCard({
  label,
  value,
  tone = "default",
  delay = 0,
}: {
  label: string;
  value: string;
  tone?: "default" | "pulse";
  delay?: number;
}) {
  return (
    <Reveal
      delay={delay}
      className="rounded-xl border border-edge bg-surface p-6 transition-colors hover:border-pulse/40"
    >
      <p
        className={`font-mono text-4xl tabular-nums tracking-tight ${
          tone === "pulse" ? "text-pulse-text" : ""
        }`}
      >
        {value}
      </p>
      <p className="mt-2 font-mono text-[11px] uppercase tracking-[0.14em] text-muted">
        {label}
      </p>
    </Reveal>
  );
}
