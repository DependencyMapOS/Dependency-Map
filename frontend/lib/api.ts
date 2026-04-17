import { apiBase } from "@/lib/api-base";
import { createClient } from "@/lib/supabase/server";

function formatFetchError(status: number, data: unknown): string {
  if (data && typeof data === "object" && "detail" in data) {
    const detail = (data as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail.map((d) => (typeof d === "object" && d && "msg" in d ? String((d as { msg: unknown }).msg) : JSON.stringify(d))).join("; ");
    }
  }
  return `HTTP ${status}`;
}

export async function apiFetchOptional(
  path: string,
): Promise<{ ok: true; data: unknown } | { ok: false; error: string }> {
  const base = apiBase();
  const url = `${base}${path.startsWith("/") ? path : `/${path}`}`;

  let token: string | undefined;
  try {
    const supabase = await createClient();
    const {
      data: { session },
    } = await supabase.auth.getSession();
    token = session?.access_token;
  } catch {
    token = undefined;
  }

  const headers = new Headers({ Accept: "application/json" });
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  try {
    const res = await fetch(url, { headers, cache: "no-store" });
    const text = await res.text();
    let data: unknown = null;
    if (text) {
      try {
        data = JSON.parse(text) as unknown;
      } catch {
        data = text;
      }
    }
    if (!res.ok) {
      return { ok: false, error: formatFetchError(res.status, data) };
    }
    return { ok: true, data };
  } catch (err) {
    const message = err instanceof Error ? err.message : "Request failed";
    return { ok: false, error: message };
  }
}
