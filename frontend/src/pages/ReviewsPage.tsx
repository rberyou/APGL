import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RotateCcw, Send } from "lucide-react";
import { api } from "../api/client";
import { EmptyState, ErrorMessage, LoadingBlock } from "../components/Layout";

export default function ReviewsPage() {
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [messages, setMessages] = useState<Record<number, string>>({});
  const queryClient = useQueryClient();
  const reviews = useQuery({ queryKey: ["reviews", "today"], queryFn: api.reviewsToday });

  const mutation = useMutation({
    mutationFn: ({ id, answer }: { id: number; answer: string }) => api.submitReview(id, answer),
    onSuccess: (result, variables) => {
      setMessages((current) => ({ ...current, [variables.id]: result.feedback }));
      queryClient.invalidateQueries({ queryKey: ["reviews", "today"] });
      queryClient.invalidateQueries({ queryKey: ["mistakes"] });
    }
  });

  if (reviews.isLoading) return <LoadingBlock label="Loading reviews" />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-ink">Today&apos;s review</h1>
        <p className="mt-1 text-sm text-slate-600">
          Revisit weak points while they are still fresh.
        </p>
      </div>
      {reviews.error ? <ErrorMessage message={reviews.error.message} /> : null}
      {mutation.error ? <ErrorMessage message={mutation.error.message} /> : null}
      {reviews.data?.length ? (
        <section className="grid gap-4 lg:grid-cols-2">
          {reviews.data.map((task) => (
            <article key={task.id} className="panel">
              <div className="mb-3 flex items-center gap-2 text-teal">
                <RotateCcw size={18} aria-hidden="true" />
                <span className="text-sm font-bold">Review prompt</span>
              </div>
              <p className="text-sm font-semibold leading-6 text-ink">{task.prompt}</p>
              <textarea
                className="field mt-3 min-h-24"
                value={answers[task.id] ?? ""}
                onChange={(event) =>
                  setAnswers((current) => ({ ...current, [task.id]: event.target.value }))
                }
                placeholder="Answer from memory"
              />
              <button
                className="btn-primary mt-3 w-full"
                disabled={mutation.isPending || !answers[task.id]?.trim()}
                onClick={() => mutation.mutate({ id: task.id, answer: answers[task.id] })}
              >
                <Send size={16} aria-hidden="true" />
                Submit review
              </button>
              {messages[task.id] ? (
                <p className="mt-3 rounded-md border border-line bg-paper p-3 text-sm leading-6 text-slate-700">
                  {messages[task.id]}
                </p>
              ) : null}
            </article>
          ))}
        </section>
      ) : (
        <EmptyState
          title="No reviews due"
          body="When you miss a quiz item, APGL schedules it here for focused follow-up."
        />
      )}
    </div>
  );
}

