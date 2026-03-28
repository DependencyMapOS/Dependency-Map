import Link from "next/link";

export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen max-w-lg flex-col justify-center gap-8 px-6 py-16">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">Dependency Map</h1>
        <p className="mt-2 text-[color:var(--muted)]">
          Static dependency graphs, blast radius, and PR summaries.
        </p>
      </div>
      <div className="flex flex-wrap gap-3">
        <Link
          href="/login"
          className="rounded-lg bg-[color:var(--accent)] px-4 py-2.5 text-sm font-medium text-[color:var(--background)]"
        >
          Log in
        </Link>
        <Link
          href="/signup"
          className="rounded-lg border border-[color:var(--border)] px-4 py-2.5 text-sm font-medium"
        >
          Sign up
        </Link>
      </div>
    </main>
  );
}
