import Link from "next/link";
import { apiFetchOptional } from "@/lib/api";

export default async function RepoPage({
  params,
}: {
  params: Promise<{ repoId: string }>;
}) {
  const { repoId } = await params;
  const latest = await apiFetchOptional(`/v1/repos/${repoId}/analyses/latest`);

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <h1 className="text-2xl font-semibold tracking-tight">Repository</h1>
      <p className="mt-1 font-mono text-sm text-[color:var(--muted)]">{repoId}</p>

      <section className="mt-8 rounded-xl border border-[color:var(--border)] bg-[color:var(--card)] p-6">
        <h2 className="text-sm font-medium uppercase tracking-wide text-[color:var(--muted)]">
          Latest analysis
        </h2>
        {latest.ok ? (
          <pre className="mt-3 max-h-96 overflow-auto rounded-lg bg-[color:var(--background)] p-3 text-xs">
            {JSON.stringify(latest.data, null, 2)}
          </pre>
        ) : (
          <p className="mt-3 text-sm text-[color:var(--muted)]">{latest.error}</p>
        )}
      </section>

      <nav className="mt-8 flex gap-4 text-sm">
        <Link href="/dashboard" className="font-medium underline">
          Dashboard
        </Link>
      </nav>
    </main>
  );
}
