"use client";

export default function Error() {
  return (
    <main className="mx-auto max-w-3xl p-8">
      <h1 className="text-2xl font-semibold">Data source unreachable</h1>
      <p className="mt-2 text-sm">
        The dashboard could not reach its data source. A paused free-tier
        database is the usual cause — the pipeline itself may still be fine.
      </p>
    </main>
  );
}
