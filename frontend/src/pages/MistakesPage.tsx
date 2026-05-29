import { useQuery } from "@tanstack/react-query";
import { TriangleAlert } from "lucide-react";
import { api } from "../api/client";
import { EmptyState, ErrorMessage, LoadingBlock } from "../components/Layout";

export default function MistakesPage() {
  const mistakes = useQuery({ queryKey: ["mistakes"], queryFn: api.mistakes });

  if (mistakes.isLoading) return <LoadingBlock label="Loading mistake book" />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-ink">Weak point center</h1>
        <p className="mt-1 text-sm text-slate-600">
          Wrong answers become reviewable weak points that guide the tutor's next sessions.
        </p>
      </div>
      {mistakes.error ? <ErrorMessage message={mistakes.error.message} /> : null}
      {mistakes.data?.length ? (
        <section className="grid gap-4">
          {mistakes.data.map((mistake) => (
            <article key={mistake.id} className="panel">
              <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                <div>
                  <div className="mb-2 flex items-center gap-2 text-ember">
                    <TriangleAlert size={18} aria-hidden="true" />
                    <span className="text-sm font-bold">Open weak point</span>
                  </div>
                  <h2 className="font-bold leading-6 text-ink">{mistake.prompt}</h2>
                </div>
                <span className="rounded-md border border-line px-2 py-1 text-xs font-semibold capitalize text-slate-600">
                  {mistake.status}
                </span>
              </div>
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                <div className="rounded-md bg-paper p-3">
                  <span className="text-xs font-bold uppercase tracking-wide text-slate-500">
                    Your answer
                  </span>
                  <p className="mt-2 text-sm leading-6 text-slate-700">{mistake.user_answer}</p>
                </div>
                <div className="rounded-md bg-amber-50 p-3">
                  <span className="text-xs font-bold uppercase tracking-wide text-amber-700">
                    Tutor feedback
                  </span>
                  <p className="mt-2 text-sm leading-6 text-amber-900">{mistake.reason}</p>
                </div>
              </div>
            </article>
          ))}
        </section>
      ) : (
        <EmptyState
          title="No mistakes recorded"
          body="Once a quiz answer needs work, it will appear here with the tutor's feedback."
        />
      )}
    </div>
  );
}
