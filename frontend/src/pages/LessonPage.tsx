import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";
import { BookOpen, Brain, MessageSquare, Send, Sparkles } from "lucide-react";
import { api } from "../api/client";
import type { AssessmentSession } from "../api/types";
import { ErrorMessage, LoadingBlock } from "../components/Layout";

export default function LessonPage() {
  const { lessonId } = useParams();
  const id = Number(lessonId);
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const assessmentSectionRef = useRef<HTMLElement | null>(null);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [assessmentId, setAssessmentId] = useState<number | null>(null);
  const [assessmentAnswer, setAssessmentAnswer] = useState("");
  const [tutorInput, setTutorInput] = useState("");

  const lesson = useQuery({
    queryKey: ["lesson", id],
    queryFn: () => api.lesson(id),
    enabled: Number.isFinite(id)
  });
  const steps = useQuery({
    queryKey: ["lesson-steps", id],
    queryFn: () => api.lessonSteps(id),
    enabled: Number.isFinite(id)
  });
  const assessment = useQuery({
    queryKey: ["assessment", assessmentId],
    queryFn: () => api.assessment(assessmentId!),
    enabled: Boolean(assessmentId),
    refetchInterval: false
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

  const prepareMutation = useMutation({
    mutationFn: () => api.prepareLesson(id),
    onSuccess: (job) => navigate(`/jobs/${job.id}?projectId=${job.project_id}`)
  });

  const startAssessmentMutation = useMutation({
    mutationFn: () => api.startAssessment(id),
    onSuccess: (data) => {
      setAssessmentId(data.id);
      queryClient.invalidateQueries({ queryKey: ["lesson", id] });
      queryClient.invalidateQueries({ queryKey: ["project-tracker", data.project_id] });
      window.setTimeout(() => {
        assessmentSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 50);
    }
  });

  const answerAssessmentMutation = useMutation({
    mutationFn: ({ target, answer }: { target: AssessmentSession; answer: string }) =>
      api.answerAssessment(target.id, answer),
    onSuccess: (data) => {
      setAssessmentAnswer("");
      setAssessmentId(data.id);
      queryClient.setQueryData(["assessment", data.id], data);
      queryClient.invalidateQueries({ queryKey: ["lesson", id] });
      queryClient.invalidateQueries({ queryKey: ["project", data.project_id] });
      queryClient.invalidateQueries({ queryKey: ["project-tracker", data.project_id] });
      queryClient.invalidateQueries({ queryKey: ["reviews", "today"] });
      queryClient.invalidateQueries({ queryKey: ["mistakes"] });
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

  const activeAssessment = assessment.data ?? startAssessmentMutation.data ?? null;
  const currentTurn = activeAssessment?.current_turn ?? null;

  if (lesson.isLoading || steps.isLoading) {
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
          <div className="mt-5 grid gap-3 sm:grid-cols-2">
            <Metric label="Lesson mastery" value={`${Math.round((lesson.data?.mastery ?? 0) * 100)}%`} />
            <Metric label="Knowledge points" value={String(lesson.data?.knowledge_points.length ?? 0)} />
          </div>
          {lesson.data?.knowledge_points.length ? (
            <div className="mt-4 flex flex-wrap gap-2">
              {lesson.data.knowledge_points.map((point) => (
                <span key={point.id} className="rounded-md bg-paper px-2 py-1 text-xs font-semibold text-slate-700">
                  {point.name} · {Math.round(point.mastery * 100)}%
                </span>
              ))}
            </div>
          ) : null}
          <div className="mt-5 flex flex-wrap gap-3">
            {!lesson.data?.content ? (
              <button
                className="btn-primary"
                disabled={prepareMutation.isPending}
                onClick={() => prepareMutation.mutate()}
              >
                <Sparkles size={16} aria-hidden="true" />
                {prepareMutation.isPending ? "Preparing" : "Prepare lesson"}
              </button>
            ) : (
              <button
                className="btn-primary"
                disabled={startAssessmentMutation.isPending}
                onClick={() => startAssessmentMutation.mutate()}
              >
                <Brain size={16} aria-hidden="true" />
                {startAssessmentMutation.isPending
                  ? "Starting quiz"
                  : activeAssessment
                    ? "Continue quiz"
                    : "Quiz me"}
              </button>
            )}
            {lesson.data ? (
              <Link className="btn-secondary" to={`/projects/${lesson.data.project_id}`}>
                Back to project
              </Link>
            ) : null}
          </div>
          {prepareMutation.error ? <div className="mt-3"><ErrorMessage message={prepareMutation.error.message} /></div> : null}
        </article>

        <section className="panel">
          <div className="mb-4 flex items-center gap-2">
            <BookOpen className="text-teal" size={20} aria-hidden="true" />
            <h2 className="text-lg font-bold text-ink">Tutor explanation</h2>
          </div>
          {lesson.data?.content ? (
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
          ) : (
            <p className="text-sm leading-6 text-slate-600">
              This lesson has a path and mapped knowledge points. Prepare it when you are ready for
              the tutor explanation.
            </p>
          )}
        </section>

        <section className="panel" ref={assessmentSectionRef}>
          <div className="mb-4 flex items-center gap-2">
            <Brain className="text-teal" size={20} aria-hidden="true" />
            <h2 className="text-lg font-bold text-ink">Dynamic assessment</h2>
          </div>
          {startAssessmentMutation.error ? (
            <div className="mb-4">
              <ErrorMessage message={startAssessmentMutation.error.message} />
            </div>
          ) : null}
          {!activeAssessment ? (
            <div className="space-y-4">
              <p className="text-sm leading-6 text-slate-600">
                Start a tutor assessment when you are ready. APGL will ask one question at a time and
                update mastery from your answers.
              </p>
              <button
                className="btn-primary"
                disabled={startAssessmentMutation.isPending || !lesson.data?.content}
                onClick={() => startAssessmentMutation.mutate()}
              >
                <Brain size={16} aria-hidden="true" />
                {startAssessmentMutation.isPending ? "Starting quiz" : "Quiz me"}
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="rounded-md bg-paper p-3 text-sm text-slate-700">
                Mastery: {Math.round(activeAssessment.lesson_mastery * 100)}% · Answered:{" "}
                {activeAssessment.turns_answered}
              </div>
              {activeAssessment.status === "completed" ? (
                <div className="rounded-md border border-teal/30 bg-teal/5 p-3 text-sm leading-6 text-teal">
                  {activeAssessment.summary || "Assessment completed."}
                </div>
              ) : currentTurn ? (
                <div className="space-y-3">
                  <p className="text-sm font-semibold leading-6 text-ink">{currentTurn.question}</p>
                  <textarea
                    className="field min-h-24"
                    value={assessmentAnswer}
                    onChange={(event) => setAssessmentAnswer(event.target.value)}
                    placeholder="Answer in your own words"
                  />
                  <button
                    className="btn-primary"
                    disabled={answerAssessmentMutation.isPending || !assessmentAnswer.trim()}
                    onClick={() =>
                      answerAssessmentMutation.mutate({
                        target: activeAssessment,
                        answer: assessmentAnswer
                      })
                    }
                  >
                    <Send size={16} aria-hidden="true" />
                    Submit answer
                  </button>
                </div>
              ) : null}
              {answerAssessmentMutation.error ? <ErrorMessage message={answerAssessmentMutation.error.message} /> : null}
              {activeAssessment.turns.filter((turn) => turn.status === "answered").slice(-3).map((turn) => (
                <div key={turn.id} className="rounded-md border border-line p-3 text-sm leading-6">
                  <div className="font-semibold text-ink">Score {Math.round((turn.score ?? 0) * 100)}%</div>
                  <p className="mt-1 text-slate-600">{turn.feedback}</p>
                </div>
              ))}
            </div>
          )}
        </section>
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
              {startSessionMutation.error ? <ErrorMessage message={startSessionMutation.error.message} /> : null}
              {sendMessageMutation.error ? <ErrorMessage message={sendMessageMutation.error.message} /> : null}
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

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-paper p-3">
      <div className="text-xs font-semibold text-slate-500">{label}</div>
      <div className="mt-1 text-base font-bold text-ink">{value}</div>
    </div>
  );
}
