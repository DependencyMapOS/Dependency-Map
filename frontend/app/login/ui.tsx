"use client";

import { createClient } from "@/lib/supabase/client";
import { useRouter } from "next/navigation";
import { use, useState } from "react";

export function LoginForm({
  nextPathPromise,
}: {
  nextPathPromise: Promise<{ next?: string }>;
}) {
  const { next: nextPath } = use(nextPathPromise);
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    const supabase = createClient();
    const { error: signError } = await supabase.auth.signInWithPassword({
      email,
      password,
    });
    setLoading(false);
    if (signError) {
      setError(signError.message);
      return;
    }
    router.push(nextPath && nextPath.startsWith("/") ? nextPath : "/dashboard");
    router.refresh();
  }

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-4">
      <div>
        <label htmlFor="email" className="mb-1 block text-sm font-medium">
          Email
        </label>
        <input
          id="email"
          name="email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full rounded-lg border border-[color:var(--border)] bg-[color:var(--card)] px-3 py-2 text-sm outline-none ring-offset-2 focus:ring-2 focus:ring-neutral-400"
        />
      </div>
      <div>
        <label htmlFor="password" className="mb-1 block text-sm font-medium">
          Password
        </label>
        <input
          id="password"
          name="password"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full rounded-lg border border-[color:var(--border)] bg-[color:var(--card)] px-3 py-2 text-sm outline-none ring-offset-2 focus:ring-2 focus:ring-neutral-400"
        />
      </div>
      {error ? (
        <p className="text-sm text-red-600 dark:text-red-400" role="alert">
          {error}
        </p>
      ) : null}
      <button
        type="submit"
        disabled={loading}
        className="rounded-lg bg-[color:var(--accent)] px-4 py-2.5 text-sm font-medium text-[color:var(--background)] disabled:opacity-60"
      >
        {loading ? "Signing in…" : "Log in"}
      </button>
    </form>
  );
}
