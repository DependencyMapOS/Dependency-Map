import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { apiFetchOptional } from "@/lib/api";
import { signOut } from "./actions";

export default async function DashboardPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  const dash = await apiFetchOptional("/v1/dashboard");

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <header className="mb-10 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
          <p className="mt-1 text-sm text-[color:var(--muted)]">
            Signed in as {user?.email ?? "—"}
          </p>
        </div>
        <form action={signOut}>
          <button
            type="submit"
            className="text-sm font-medium text-[color:var(--muted)] underline"
          >
            Sign out
          </button>
        </form>
      </header>

      <section className="rounded-xl border border-[color:var(--border)] bg-[color:var(--card)] p-6">
        <h2 className="text-sm font-medium uppercase tracking-wide text-[color:var(--muted)]">
          API status
        </h2>
        {dash.ok ? (
          <pre className="mt-3 max-h-64 overflow-auto rounded-lg bg-[color:var(--background)] p-3 text-xs">
            {JSON.stringify(dash.data, null, 2)}
          </pre>
        ) : (
          <p className="mt-3 text-sm text-[color:var(--muted)]">
            {dash.error ?? "Connect the API (see backend/) and set API_URL."}
          </p>
        )}
      </section>

      <nav className="mt-8 flex flex-wrap gap-4 text-sm">
        <Link href="/orgs/demo/repos" className="font-medium underline">
          Repos (sample org route)
        </Link>
        <Link href="/repos/demo" className="font-medium underline">
          Repo detail (placeholder slug — API needs a UUID)
        </Link>
      </nav>
    </main>
  );
}
