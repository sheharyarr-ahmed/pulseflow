export default async function JobPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <main className="mx-auto max-w-3xl p-8">
      <h1 className="text-2xl font-semibold">Job {id}</h1>
      <p className="mt-2 text-sm">
        Score, reasoning, snippet and outbound source link land here at Phase 3.
      </p>
    </main>
  );
}
