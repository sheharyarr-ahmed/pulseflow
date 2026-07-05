import Link from "next/link";
import PulseLine from "@/components/PulseLine";

export default function JobNotFound() {
  return (
    <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-16 md:px-10">
      <div className="rounded-xl border border-edge bg-surface p-6 md:p-8">
        <PulseLine state="flat" className="max-w-md" />
        <h1 className="mt-6 text-xl font-semibold tracking-tight">
          This job was never seen by the pipeline.
        </h1>
        <p className="mt-2 text-sm text-muted">
          It may have expired from the feed before a run picked it up, or the
          link is stale.
        </p>
        <Link
          href="/"
          className="mt-6 inline-block rounded-lg border border-edge px-5 py-2.5 text-sm font-medium transition-colors hover:border-pulse/40"
        >
          ← Back to overview
        </Link>
      </div>
    </main>
  );
}
