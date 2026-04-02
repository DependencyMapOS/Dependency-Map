import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { apiFetchOptional } from "@/lib/api";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

type DashboardPayload = {
  organizations?: unknown[];
  user_id?: string;
  email?: string | null;
  message?: string;
};

export default async function DashboardPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  const dash = await apiFetchOptional("/v1/dashboard");
  const data = dash.ok ? (dash.data as DashboardPayload) : null;
  const orgCount = Array.isArray(data?.organizations) ? data.organizations.length : 0;

  return (
    <main className="mx-auto max-w-4xl px-4 py-8 md:px-8">
      <header className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Signed in as <span className="font-medium text-foreground">{user?.email ?? "—"}</span>
        </p>
      </header>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Organizations</CardDescription>
            <CardTitle className="text-3xl tabular-nums">{orgCount}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground">
              Linked workspaces from the API. Wire Supabase queries to populate.
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>API</CardDescription>
            <CardTitle className="flex items-center gap-2 text-lg">
              {dash.ok ? (
                <Badge variant="secondary">Connected</Badge>
              ) : (
                <Badge variant="destructive">Offline</Badge>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground">
              {dash.ok ? "FastAPI returned dashboard payload." : (dash.error ?? "Set API_URL / backend.")}
            </p>
          </CardContent>
        </Card>
        <Card className="sm:col-span-2 lg:col-span-1">
          <CardHeader className="pb-2">
            <CardDescription>Quick links</CardDescription>
            <CardTitle className="text-base">Navigation</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2 text-sm">
            <Link href="/orgs/demo/repos" className="text-primary underline-offset-4 hover:underline">
              Sample org repos
            </Link>
            <Link href="/repos/demo" className="text-primary underline-offset-4 hover:underline">
              Repo detail (use UUID in production)
            </Link>
          </CardContent>
        </Card>
      </div>

      {dash.ok && data ? (
        <Card className="mt-6">
          <CardHeader>
            <CardTitle className="text-base">Raw API response</CardTitle>
            <CardDescription>Debug view — replace with PR and analysis feeds.</CardDescription>
          </CardHeader>
          <CardContent>
            <pre className="max-h-64 overflow-auto rounded-lg border border-border bg-muted/30 p-3 text-xs">
              {JSON.stringify(data, null, 2)}
            </pre>
          </CardContent>
        </Card>
      ) : null}
    </main>
  );
}
