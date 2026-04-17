/**
 * Repo root `.env` is loaded via `loadEnvConfig(..., forceReload)` in `frontend/next.config.ts`
 * so monorepo shared vars win over cached app-dir env. Optional: `frontend/.env.local` for local overrides.
 */
export function getSupabasePublishableEnv():
  | { url: string; anonKey: string }
  | null {
  // Use direct `process.env.NEXT_PUBLIC_*` access (no `?.` on env) so Next can inline values into the client bundle.
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (url == null || anonKey == null) return null;
  const trimmedUrl = url.trim();
  const trimmedKey = anonKey.trim();
  if (!trimmedUrl || !trimmedKey) return null;
  if (trimmedUrl.includes("YOUR_PROJECT") || trimmedKey === "your_anon_key") {
    return null;
  }
  return { url: trimmedUrl, anonKey: trimmedKey };
}

export function requireSupabasePublishableEnv(): {
  url: string;
  anonKey: string;
} {
  const env = getSupabasePublishableEnv();
  if (!env) {
    throw new Error(
      "Supabase URL and anon key are missing or still placeholders. Set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY in the repo root .env or frontend/.env.local (see .env.example and https://supabase.com/dashboard/project/_/settings/api ).",
    );
  }
  return env;
}
