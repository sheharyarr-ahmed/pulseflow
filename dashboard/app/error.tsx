"use client";

import PulseLine from "@/components/PulseLine";

export default function Error({ reset }: { error: Error; reset: () => void }) {
  return (
    <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-16 md:px-10">
      <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-6 md:p-8">
        <PulseLine state="warn" className="max-w-md" />
        <h1 className="mt-6 text-xl font-semibold tracking-tight">
          Flatline — data source unreachable
        </h1>
        <p className="mt-2 max-w-xl text-sm text-muted">
          The dashboard could not reach its data source. A paused free-tier
          database is the usual cause — the pipeline itself may still be fine.
        </p>
        <button
          type="button"
          onClick={reset}
          className="mt-6 rounded-lg border border-edge px-5 py-2.5 text-sm font-medium transition-colors hover:border-pulse/40"
        >
          Try again
        </button>
      </div>
    </main>
  );
}
