import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { CheckCircle2, Send, SquareCheckBig } from "lucide-react";
import { api } from "../api/client";
import type { AnswerResult } from "../api/types";
import { ErrorMessage, LoadingBlock } from "../components/Layout";

export default function LessonPage() {
  const { lessonId } = useParams();
  const id = Number(lessonId);
  const queryClient = useQueryClient();
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [results, setResults] = useState<Record<number, AnswerResult>>({});

  const lesson = useQuery({
    queryKey: ["lesson", id],
    queryFn: () => api.lesson(id),
    enabled: Number.isFinite(id)
  });
  const quiz = useQuery({
    queryKey: ["quiz", id],
    queryFn: () => api.quiz(id),
    enabled: Number.isFinite(id)
  });

  const answerMutation = useMutation({
    mutationFn: ({ quizId, answer }: { quizId: number; answer: string }) =>
      api.answerQuiz(quizId, answer),
    onSuccess: (result, variables) => {
      setResults((current) => ({ ...current, [variables.quizId]: result }));
      queryClient.invalidateQueries({ queryKey: ["reviews", "today"] });
      queryClient.invalidateQueries({ queryKey: ["mistakes"] });
    }
  });

  const completeMutation = useMutation({
    mutationFn: () => api.completeLesson(id),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: ["project", updated.project_id] });
      queryClient.invalidateQueries({ queryKey: ["lessons", updated.project_id] });
      queryClient.invalidateQueries({ queryKey: ["lesson", id] });
    }
  });

  if (lesson.isLoading || quiz.isLoading) return <LoadingBlock label="Loading lesson" />;
  if (lesson.error) return <ErrorMessage message={lesson.error.message} />;

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
      <article className="panel">
        <span className="text-xs font-bold uppercase tracking-wide text-ember">
          Lesson {lesson.data?.order_index}
        </span>
        <h1 className="mt-2 text-2xl font-bold text-ink">{lesson.data?.title}</h1>
        <p className="mt-3 text-sm leading-6 text-slate-600">{lesson.data?.summary}</p>
        <div className="mt-6 whitespace-pre-wrap rounded-md border border-line bg-paper p-4 text-sm leading-7 text-ink">
          {lesson.data?.content}
        </div>
        <div className="mt-5 flex flex-wrap gap-3">
          <button
            className="btn-primary"
            onClick={() => completeMutation.mutate()}
            disabled={completeMutation.isPending || lesson.data?.status === "completed"}
          >
            <SquareCheckBig size={16} aria-hidden="true" />
            {lesson.data?.status === "completed" ? "Completed" : "Mark complete"}
          </button>
          {lesson.data ? (
            <Link className="btn-secondary" to={`/projects/${lesson.data.project_id}`}>
              Back to project
            </Link>
          ) : null}
        </div>
      </article>

      <aside className="space-y-4">
        <div>
          <h2 className="text-lg font-bold text-ink">Check understanding</h2>
          <p className="mt-1 text-sm text-slate-600">
            Answer in your own words; weak points go to review.
          </p>
        </div>
        {answerMutation.error ? <ErrorMessage message={answerMutation.error.message} /> : null}
        {quiz.data?.map((item) => {
          const result = results[item.id];
          return (
            <section key={item.id} className="panel">
              <p className="text-sm font-semibold leading-6 text-ink">{item.prompt}</p>
              <textarea
                className="field mt-3 min-h-24"
                value={answers[item.id] ?? ""}
                onChange={(event) =>
                  setAnswers((current) => ({ ...current, [item.id]: event.target.value }))
                }
                placeholder="Type your answer"
              />
              <button
                className="btn-primary mt-3 w-full"
                disabled={answerMutation.isPending || !answers[item.id]?.trim()}
                onClick={() =>
                  answerMutation.mutate({ quizId: item.id, answer: answers[item.id] })
                }
              >
                <Send size={16} aria-hidden="true" />
                Submit
              </button>
              {result ? (
                <div
                  className={`mt-3 rounded-md border p-3 text-sm leading-6 ${
                    result.is_correct
                      ? "border-teal/30 bg-teal/5 text-teal"
                      : "border-amber-200 bg-amber-50 text-amber-800"
                  }`}
                >
                  <div className="mb-1 flex items-center gap-2 font-bold">
                    <CheckCircle2 size={16} aria-hidden="true" />
                    {result.is_correct ? "Looks good" : "Review needed"}
                  </div>
                  <p>{result.feedback}</p>
                  {result.explanation ? <p className="mt-2">{result.explanation}</p> : null}
                </div>
              ) : null}
            </section>
          );
        })}
      </aside>
    </div>
  );
}

