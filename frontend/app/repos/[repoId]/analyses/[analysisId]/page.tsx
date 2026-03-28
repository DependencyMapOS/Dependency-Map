import Link from "next/link";
import { apiFetchOptional } from "@/lib/api";

export default async function AnalysisPage({
  params,
}: {
  params: Promise<{ repoId: string; analysisId: string }>;
}) {
  const { repoId, analysisId } = await params;
  const res = await apiFetchOptional(
    `/v1/repos/${repoId}/analyses/${analysisId}`,
  );

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
    <main className="mx-auto max-w-3xl px-6 py-12">
      <h1 className="text-2xl font-semibold tracking-tight">Analysis</h1>
      <p className="mt-1 font-mono text-sm text-[color:var(--muted)]">
        {repoId} / {analysisId}
      </p>

      <section className="mt-8 space-y-6">
        {res.ok && summary && typeof summary === "object" && summary !== null ? (
          <AnalysisSummary summary={summary as Record<string, unknown>} />
        ) : (
          <pre className="max-h-96 overflow-auto rounded-xl border border-[color:var(--border)] bg-[color:var(--card)] p-4 text-xs">
            {res.ok
              ? JSON.stringify(res.data, null, 2)
              : res.error}
          </pre>
        )}
      </section>

      <Link
        href={`/repos/${repoId}`}
        className="mt-8 inline-block text-sm font-medium underline"
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
    <div className="space-y-6">
      {sections.map(({ key, label }) => {
        const value = summary[key];
        if (value === undefined) return null;
        return (
          <div
            key={key}
            className="rounded-xl border border-[color:var(--border)] bg-[color:var(--card)] p-4"
          >
            <h2 className="text-sm font-medium text-[color:var(--muted)]">{label}</h2>
            <div className="mt-2 text-sm">
              {Array.isArray(value) ? (
                <ul className="list-inside list-disc space-y-1">
                  {value.map((item, i) => (
                    <li key={i}>
                      {typeof item === "object"
                        ? JSON.stringify(item)
                        : String(item)}
                    </li>
                  ))}
                </ul>
              ) : typeof value === "object" && value !== null ? (
                <pre className="overflow-auto text-xs">
                  {JSON.stringify(value, null, 2)}
                </pre>
              ) : (
                String(value)
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
