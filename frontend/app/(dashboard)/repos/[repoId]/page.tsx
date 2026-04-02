import Link from "next/link";
import { apiFetchOptional } from "@/lib/api";
import { isValidUuid } from "@/lib/uuid";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default async function RepoPage({
  params,
}: {
  params: Promise<{ repoId: string }>;
}) {
  const { repoId } = await params;
  const latest = isValidUuid(repoId)
    ? await apiFetchOptional(`/v1/repos/${repoId}/analyses/latest`)
    : {
        ok: false as const,
        error:
          "The API expects a repository UUID in the URL (from your database), not a short name like “demo”.",
      };

  return (
    <main className="mx-auto max-w-4xl px-4 py-8 md:px-8">
      <h1 className="text-2xl font-semibold tracking-tight">Repository</h1>
      <p className="mt-1 font-mono text-sm text-muted-foreground">{repoId}</p>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="text-base">Latest analysis</CardTitle>
          <CardDescription>Most recent completed or running job for this repo.</CardDescription>
        </CardHeader>
        <CardContent>
          {latest.ok ? (
            <pre className="max-h-96 overflow-auto rounded-lg border border-border bg-muted/30 p-3 text-xs">
              {JSON.stringify(latest.data, null, 2)}
            </pre>
          ) : (
            <p className="text-sm text-muted-foreground">{latest.error}</p>
          )}
        </CardContent>
      </Card>

      <Link href="/dashboard" className="mt-8 inline-block text-sm font-medium text-primary hover:underline">
        Dashboard
      </Link>
    </main>
  );
}
