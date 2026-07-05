// The brand's EKG line as a live instrument (server component, pure CSS
// animation — works without JS). Three states carry the app's health
// language: "live" draws the waveform and ignites the breathing emerald dot,
// "flat" is the quiet empty-state line, "warn" is the amber flatline used by
// unreachable/error states.
type PulseLineState = "live" | "flat" | "warn";

const PATHS: Record<PulseLineState, string> = {
  live: "M0 32 H440 L466 6 L494 58 L512 32 H744",
  flat: "M0 32 H500 L512 24 L524 32 H744",
  warn: "M0 32 H744",
};

const STROKE: Record<PulseLineState, string> = {
  live: "text-pulse",
  flat: "text-zinc-300 dark:text-zinc-700",
  warn: "text-amber-500/70",
};

const DOT: Record<PulseLineState, string> = {
  live: "fill-pulse",
  flat: "fill-zinc-400 dark:fill-zinc-600",
  warn: "fill-amber-500",
};

export default function PulseLine({
  state = "live",
  className = "",
}: {
  state?: PulseLineState;
  className?: string;
}) {
  return (
    <svg
      viewBox="0 0 800 64"
      preserveAspectRatio="none"
      aria-hidden
      className={`h-16 w-full ${STROKE[state]} ${className}`}
    >
      <path
        d={PATHS[state]}
        pathLength={1}
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        vectorEffect="non-scaling-stroke"
        className="ekg-path"
      />
      {state === "live" && (
        <circle cx="768" cy="32" r="5" className="ekg-halo fill-pulse" />
      )}
      <circle
        cx="768"
        cy="32"
        r="5"
        className={`${DOT[state]} ${state === "live" ? "ekg-dot" : ""}`}
      />
    </svg>
  );
}
