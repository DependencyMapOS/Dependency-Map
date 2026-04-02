import Link from "next/link";
import { apiFetchOptional } from "@/lib/api";
import { isValidUuid } from "@/lib/uuid";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default async function AnalysisPage({
  params,
}: {
  params: Promise<{ repoId: string; analysisId: string }>;
}) {
  const { repoId, analysisId } = await params;
  const res =
    isValidUuid(repoId) && isValidUuid(analysisId)
      ? await apiFetchOptional(`/v1/repos/${repoId}/analyses/${analysisId}`)
      : {
          ok: false as const,
          error:
            "Repository and analysis IDs in the URL must be UUIDs. Sample paths like /repos/demo are placeholders only.",
        };

  const summary =
    res.ok &&
    res.data &&
    typeof res.data === "object" &&
    res.data !== null &&
    "summary_json" in res.data
      ? (res.data as { summary_json?: unknown }).summary_json
      : res.ok
        ? res.data
        : null;

  return (
    <main className="mx-auto max-w-4xl px-4 py-8 md:px-8">
      <h1 className="text-2xl font-semibold tracking-tight">Analysis</h1>
      <p className="mt-1 font-mono text-sm text-muted-foreground">
        {repoId} / {analysisId}
      </p>

      <section className="mt-8 space-y-6">
        {res.ok && summary && typeof summary === "object" && summary !== null ? (
          <AnalysisSummary summary={summary as Record<string, unknown>} />
        ) : (
          <Card>
            <CardContent className="pt-6">
              <pre className="max-h-96 overflow-auto text-xs">
                {res.ok ? JSON.stringify(res.data, null, 2) : res.error}
              </pre>
            </CardContent>
          </Card>
        )}
      </section>

      <Link
        href={`/repos/${repoId}`}
        className="mt-8 inline-block text-sm font-medium text-primary hover:underline"
      >
        Back to repo
      </Link>
    </main>
  );
}

function AnalysisSummary({ summary }: { summary: Record<string, unknown> }) {
  const sections: { key: string; label: string }[] = [
    { key: "changed_files", label: "Changed files" },
    { key: "changed_dependency_edges", label: "Dependency edge changes" },
    { key: "impacted_modules", label: "Impacted modules" },
    { key: "blast_radius_score", label: "Blast radius score" },
    { key: "suggested_reviewers", label: "Suggested reviewers" },
    { key: "risks", label: "Risks" },
  ];

  return (
    <div className="space-y-4">
      {sections.map(({ key, label }) => {
        const value = summary[key];
        if (value === undefined) return null;
        return (
          <Card key={key}>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">{label}</CardTitle>
            </CardHeader>
            <CardContent className="text-sm">
              {Array.isArray(value) ? (
                <ul className="list-inside list-disc space-y-1">
                  {value.map((item, i) => (
                    <li key={i}>
                      {typeof item === "object" ? JSON.stringify(item) : String(item)}
                    </li>
                  ))}
                </ul>
              ) : typeof value === "object" && value !== null ? (
                <pre className="overflow-auto text-xs">{JSON.stringify(value, null, 2)}</pre>
              ) : (
                String(value)
              )}
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
