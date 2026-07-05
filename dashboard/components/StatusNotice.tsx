import PulseLine from "./PulseLine";

// Shared "data source unreachable" state. Renders inside the normal shell
// (nav + footer stay), so a paused free-tier database still looks like a
// designed site, not a broken portfolio page.
export default function StatusNotice({
  title = "Flatline — data source unreachable",
  children,
}: {
  title?: string;
  children: React.ReactNode;
}) {
  return (
    <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-16 md:px-10">
      <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-6 md:p-8">
        <PulseLine state="warn" className="max-w-md" />
        <h1 className="mt-6 text-xl font-semibold tracking-tight">{title}</h1>
        <div className="mt-2 max-w-xl text-sm text-muted">{children}</div>
      </div>
    </main>
  );
}
