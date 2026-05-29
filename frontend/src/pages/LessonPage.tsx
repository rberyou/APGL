import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import {
  BookOpen,
  CheckCircle2,
  MessageSquare,
  Send,
  Sparkles,
  SquareCheckBig
} from "lucide-react";
import { api } from "../api/client";
import type { AnswerResult } from "../api/types";
import { ErrorMessage, LoadingBlock } from "../components/Layout";

export default function LessonPage() {
  const { lessonId } = useParams();
  const id = Number(lessonId);
  const queryClient = useQueryClient();
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [results, setResults] = useState<Record<number, AnswerResult>>({});
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [tutorInput, setTutorInput] = useState("");

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
  const steps = useQuery({
    queryKey: ["lesson-steps", id],
    queryFn: () => api.lessonSteps(id),
    enabled: Number.isFinite(id)
  });
  const sessions = useQuery({
    queryKey: ["sessions", lesson.data?.project_id],
    queryFn: () => api.sessions(lesson.data!.project_id),
    enabled: Boolean(lesson.data?.project_id)
  });
  const activeSession =
    sessionId ??
    sessions.data?.find((item) => item.lesson_id === id && item.status === "active")?.id ??
    null;
  const messages = useQuery({
    queryKey: ["session-messages", activeSession],
    queryFn: () => api.sessionMessages(activeSession!),
    enabled: Boolean(activeSession)
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

  const startSessionMutation = useMutation({
    mutationFn: () =>
      api.startSession(lesson.data!.project_id, {
        lesson_id: id,
        focus: lesson.data?.title
      }),
    onSuccess: (session) => {
      setSessionId(session.id);
      queryClient.invalidateQueries({ queryKey: ["sessions", lesson.data?.project_id] });
      queryClient.invalidateQueries({ queryKey: ["session-messages", session.id] });
    }
  });

  const sendMessageMutation = useMutation({
    mutationFn: () => api.sendTutorMessage(activeSession!, tutorInput),
    onSuccess: () => {
      setTutorInput("");
      queryClient.invalidateQueries({ queryKey: ["session-messages", activeSession] });
      queryClient.invalidateQueries({ queryKey: ["project-tracker", lesson.data?.project_id] });
    }
  });

  const endSessionMutation = useMutation({
    mutationFn: () => api.endSession(activeSession!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sessions", lesson.data?.project_id] });
      queryClient.invalidateQueries({ queryKey: ["project-tracker", lesson.data?.project_id] });
    }
  });

  if (lesson.isLoading || quiz.isLoading || steps.isLoading) {
    return <LoadingBlock label="Loading tutor workspace" />;
  }
  if (lesson.error) return <ErrorMessage message={lesson.error.message} />;

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_420px]">
      <div className="space-y-6">
        <article className="panel">
          <span className="text-xs font-bold uppercase tracking-wide text-ember">
            Lesson {lesson.data?.order_index}
          </span>
          <h1 className="mt-2 text-2xl font-bold text-ink">{lesson.data?.title}</h1>
          <p className="mt-3 text-sm leading-6 text-slate-600">{lesson.data?.summary}</p>
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

        <section className="panel">
          <div className="mb-4 flex items-center gap-2">
            <BookOpen className="text-teal" size={20} aria-hidden="true" />
            <h2 className="text-lg font-bold text-ink">Guided lesson steps</h2>
          </div>
          <div className="space-y-4">
            {steps.data?.map((step) => (
              <div key={step.id} className="rounded-md border border-line p-4">
                <div className="mb-2 flex items-center justify-between gap-3">
                  <span className="text-xs font-bold uppercase tracking-wide text-ember">
                    {step.step_type}
                  </span>
                  <span className="text-xs font-semibold text-slate-500">Step {step.order_index}</span>
                </div>
                <h3 className="font-bold text-ink">{step.title}</h3>
                <p className="mt-2 whitespace-pre-wrap text-sm leading-7 text-slate-700">
                  {step.body}
                </p>
              </div>
            ))}
          </div>
        </section>

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
      </div>

      <aside className="space-y-4">
        <section className="panel">
          <div className="mb-4 flex items-center gap-2">
            <MessageSquare className="text-teal" size={20} aria-hidden="true" />
            <h2 className="text-lg font-bold text-ink">AI tutor</h2>
          </div>
          {!activeSession ? (
            <div className="space-y-3">
              <p className="text-sm leading-6 text-slate-600">
                Start a tutor session to ask questions, get examples, and leave a session note for
                this learning space.
              </p>
              <button
                className="btn-primary w-full"
                disabled={startSessionMutation.isPending || !lesson.data}
                onClick={() => startSessionMutation.mutate()}
              >
                <Sparkles size={16} aria-hidden="true" />
                Start tutor session
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              {startSessionMutation.error ? (
                <ErrorMessage message={startSessionMutation.error.message} />
              ) : null}
              {sendMessageMutation.error ? (
                <ErrorMessage message={sendMessageMutation.error.message} />
              ) : null}
              <div className="max-h-[520px] space-y-3 overflow-y-auto pr-1">
                {messages.data?.map((message) => (
                  <div
                    key={message.id}
                    className={`rounded-md p-3 text-sm leading-6 ${
                      message.role === "user"
                        ? "bg-teal text-white"
                        : "border border-line bg-paper text-slate-800"
                    }`}
                  >
                    <p className="whitespace-pre-wrap">{message.content}</p>
                    {message.citations.length ? (
                      <div className="mt-3 space-y-2 border-t border-line/70 pt-3">
                        {message.citations.slice(0, 3).map((citation) => (
                          <div key={`${citation.chunk_id}-${citation.locator}`} className="text-xs leading-5 text-slate-600">
                            <span className="font-bold text-teal">
                              {citation.locator || citation.title}
                            </span>{" "}
                            {citation.excerpt}
                          </div>
                        ))}
                      </div>
                    ) : null}
                  </div>
                ))}
              </div>
              <textarea
                className="field min-h-24"
                value={tutorInput}
                onChange={(event) => setTutorInput(event.target.value)}
                placeholder="Ask the tutor, request an example, or explain your current understanding"
              />
              <div className="grid gap-2 md:grid-cols-2">
                <button
                  className="btn-primary"
                  disabled={sendMessageMutation.isPending || !tutorInput.trim()}
                  onClick={() => sendMessageMutation.mutate()}
                >
                  <Send size={16} aria-hidden="true" />
                  Send
                </button>
                <button
                  className="btn-secondary"
                  disabled={endSessionMutation.isPending}
                  onClick={() => endSessionMutation.mutate()}
                >
                  End session
                </button>
              </div>
            </div>
          )}
        </section>
      </aside>
    </div>
  );
}
