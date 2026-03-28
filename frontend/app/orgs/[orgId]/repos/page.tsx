import Link from "next/link";

export default async function OrgReposPage({
  params,
}: {
  params: Promise<{ orgId: string }>;
}) {
  const { orgId } = await params;

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <h1 className="text-2xl font-semibold tracking-tight">Repositories</h1>
      <p className="mt-1 text-sm text-[color:var(--muted)]">
        Organization: <code className="rounded bg-[color:var(--border)] px-1">{orgId}</code>
      </p>
      <p className="mt-6 text-sm text-[color:var(--muted)]">
        Connect GitHub and sync repos via the API; this route will list linked
        repositories once ingestion is wired.
      </p>
      <Link href="/dashboard" className="mt-8 inline-block text-sm font-medium underline">
        Back to dashboard
      </Link>
    </main>
  );
}
