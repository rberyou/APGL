import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  BookOpen,
  Brain,
  CheckCircle2,
  Database,
  GitBranch,
  MessageSquare,
  Play,
  Sparkles,
  TriangleAlert
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { EmptyState, ErrorMessage, LoadingBlock } from "../components/Layout";

function statusLabel(status: string) {
  if (status === "completed") return "Completed";
  if (status === "pending") return "To learn";
  return status;
}

export default function ProjectDetailPage() {
  const { projectId } = useParams();
  const id = Number(projectId);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const project = useQuery({
    queryKey: ["project", id],
    queryFn: () => api.project(id),
    enabled: Number.isFinite(id)
  });
  const lessons = useQuery({
    queryKey: ["lessons", id],
    queryFn: () => api.lessons(id),
    enabled: Number.isFinite(id)
  });
  const latestJob = useQuery({
    queryKey: ["latest-job", id],
    queryFn: () => api.latestProjectJob(id),
    enabled: Number.isFinite(id) && project.data?.status === "failed"
  });
  const tracker = useQuery({
    queryKey: ["project-tracker", id],
    queryFn: () => api.projectTracker(id),
    enabled: Number.isFinite(id)
  });
  const knowledgeMap = useQuery({
    queryKey: ["knowledge-map", id],
    queryFn: () => api.knowledgeMap(id),
    enabled: Number.isFinite(id)
  });
  const materialStatus = useQuery({
    queryKey: ["material-status", id],
    queryFn: () => api.materialStatus(id),
    enabled: Number.isFinite(id) && project.data?.source_type === "material"
  });
  const sessions = useQuery({
    queryKey: ["sessions", id],
    queryFn: () => api.sessions(id),
    enabled: Number.isFinite(id)
  });
  const generateMutation = useMutation({
    mutationFn: () => api.generateProject(id),
    onSuccess: (response) => {
      queryClient.invalidateQueries({ queryKey: ["project", id] });
      queryClient.invalidateQueries({ queryKey: ["lessons", id] });
      queryClient.invalidateQueries({ queryKey: ["latest-job", id] });
      if (response.job_id) {
        navigate(`/jobs/${response.job_id}?projectId=${response.project.id}`);
      }
    }
  });

  if (project.isLoading || lessons.isLoading) return <LoadingBlock label="Loading project" />;
  if (project.error) return <ErrorMessage message={project.error.message} />;

  return (
    <div className="space-y-6">
      <section className="panel">
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div>
            <span className="text-xs font-bold uppercase tracking-wide text-ember">
              {project.data?.source_type}
            </span>
            <h1 className="mt-2 text-2xl font-bold text-ink">{project.data?.title}</h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-600">
              {project.data?.goal}
            </p>
          </div>
          <span className="inline-flex min-h-8 items-center rounded-md border border-line px-3 text-sm font-semibold capitalize text-slate-600">
            {project.data?.status}
          </span>
        </div>
        {project.data?.status === "failed" ? (
          <div className="mt-5 rounded-md border border-red-200 bg-red-50 p-4 text-sm leading-6 text-red-800">
            <div className="mb-1 flex items-center gap-2 font-bold">
              <TriangleAlert size={16} aria-hidden="true" />
              Generation failed
            </div>
            <p>
              {latestJob.data?.error ||
                "The latest generation job failed, but no detailed error was recorded."}
            </p>
            <p className="mt-2">
              Check your LLM configuration, then use Generate learning path below to retry.
            </p>
          </div>
        ) : null}
        <div className="mt-6">
          <div className="mb-2 flex items-center justify-between text-xs font-semibold text-slate-500">
            <span>Mastery</span>
            <span>
              {Math.round((tracker.data?.mastery ?? (project.data?.progress_percent ?? 0) / 100) * 100)}%
            </span>
          </div>
          <div className="h-2 rounded-full bg-slate-100">
            <div
              className="h-2 rounded-full bg-teal"
              style={{
                width: `${Math.round(
                  (tracker.data?.mastery ?? (project.data?.progress_percent ?? 0) / 100) * 100
                )}%`
              }}
            />
          </div>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-[1.15fr_0.85fr]">
        <div className="panel">
          <div className="mb-4 flex items-center gap-2">
            <Brain className="text-teal" size={20} aria-hidden="true" />
            <h2 className="text-lg font-bold text-ink">Tutor tracker</h2>
          </div>
          <p className="text-sm leading-6 text-slate-700">
            {tracker.data?.next_plan || "Start a tutor session to build the next plan."}
          </p>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <div className="rounded-md bg-paper p-3">
              <span className="text-xs font-bold uppercase tracking-wide text-slate-500">
                Mastered topics
              </span>
              <div className="mt-2 flex flex-wrap gap-2">
                {tracker.data?.mastered_topics.length ? (
                  tracker.data.mastered_topics.map((topic) => (
                    <span key={topic} className="rounded-md bg-teal/10 px-2 py-1 text-xs font-semibold text-teal">
                      {topic}
                    </span>
                  ))
                ) : (
                  <span className="text-sm text-slate-500">No topics marked mastered yet.</span>
                )}
              </div>
            </div>
            <div className="rounded-md bg-paper p-3">
              <span className="text-xs font-bold uppercase tracking-wide text-slate-500">
                Weak areas
              </span>
              <div className="mt-2 space-y-2">
                {tracker.data?.learning_gaps.length ? (
                  tracker.data.learning_gaps.slice(0, 3).map((gap) => (
                    <div key={`${gap.title}-${gap.severity}`} className="text-sm leading-5 text-slate-700">
                      <span className="font-semibold capitalize text-amber-700">{gap.severity}</span>{" "}
                      {gap.title}
                    </div>
                  ))
                ) : (
                  <span className="text-sm text-slate-500">No weak areas recorded yet.</span>
                )}
              </div>
            </div>
          </div>
        </div>

        <div className="panel">
          <div className="mb-4 flex items-center gap-2">
            <Database className="text-teal" size={20} aria-hidden="true" />
            <h2 className="text-lg font-bold text-ink">Source library</h2>
          </div>
          {project.data?.source_type === "material" ? (
            <div className="space-y-3 text-sm leading-6 text-slate-700">
              <p>{materialStatus.data?.message || "Material status is loading."}</p>
              <div className="grid grid-cols-2 gap-2">
                <Metric label="Pages" value={materialStatus.data?.page_count ?? 0} />
                <Metric label="Text pages" value={materialStatus.data?.text_page_count ?? 0} />
                <Metric label="Chunks" value={materialStatus.data?.chunk_count ?? 0} />
                <Metric label="Characters" value={materialStatus.data?.character_count ?? 0} />
              </div>
            </div>
          ) : (
            <p className="text-sm leading-6 text-slate-700">
              This learning space started from a skill goal. Upload support can be added later if
              you want to attach source material to it.
            </p>
          )}
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-[1fr_0.9fr]">
        <div className="panel">
          <div className="mb-4 flex items-center gap-2">
            <GitBranch className="text-teal" size={20} aria-hidden="true" />
            <h2 className="text-lg font-bold text-ink">Knowledge map</h2>
          </div>
          {knowledgeMap.data?.nodes.length ? (
            <div className="space-y-3">
              {knowledgeMap.data.nodes.slice(0, 8).map((node) => (
                <div key={node.id} className="rounded-md border border-line p-3">
                  <div className="flex items-center justify-between gap-3">
                    <h3 className="text-sm font-bold text-ink">{node.name}</h3>
                    <span className="text-xs font-semibold text-slate-500">
                      {Math.round(node.mastery * 100)}%
                    </span>
                  </div>
                  <p className="mt-1 text-sm leading-5 text-slate-600">{node.explanation}</p>
                  {node.lesson_titles.length ? (
                    <p className="mt-2 text-xs font-semibold text-teal">
                      Lessons: {node.lesson_titles.join(", ")}
                    </p>
                  ) : null}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-600">Generate a learning path to build the map.</p>
          )}
        </div>

        <div className="panel">
          <div className="mb-4 flex items-center gap-2">
            <MessageSquare className="text-teal" size={20} aria-hidden="true" />
            <h2 className="text-lg font-bold text-ink">Recent sessions</h2>
          </div>
          {sessions.data?.length ? (
            <div className="space-y-3">
              {sessions.data.slice(0, 5).map((session) => (
                <div key={session.id} className="rounded-md bg-paper p-3">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm font-bold text-ink">{session.focus}</span>
                    <span className="text-xs font-semibold capitalize text-slate-500">
                      {session.status}
                    </span>
                  </div>
                  {session.summary ? (
                    <p className="mt-2 text-sm leading-5 text-slate-600">{session.summary}</p>
                  ) : null}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm leading-6 text-slate-600">
              Open a lesson and start a tutor session. APGL will keep the session notes here.
            </p>
          )}
        </div>
      </section>

      {lessons.error ? <ErrorMessage message={lessons.error.message} /> : null}
      {generateMutation.error ? <ErrorMessage message={generateMutation.error.message} /> : null}

      {lessons.data?.length ? (
        <section className="space-y-3">
          <div>
            <h2 className="text-lg font-bold text-ink">Tutor learning path</h2>
            <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
              Each lesson opens a tutor workspace with guided steps, chat, source references,
              checks, mistakes, and review.
            </p>
          </div>
          <div className="grid gap-4">
            {lessons.data.map((lesson, index) => (
              <Link
                key={lesson.id}
                to={`/lessons/${lesson.id}`}
                className="panel flex flex-col gap-4 transition hover:border-teal md:flex-row md:items-center md:justify-between"
              >
                <div className="flex gap-4">
                  <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-paper text-teal">
                    {lesson.status === "completed" ? (
                      <CheckCircle2 size={20} aria-hidden="true" />
                    ) : (
                      <BookOpen size={20} aria-hidden="true" />
                    )}
                  </span>
                  <div>
                    <span className="text-xs font-bold uppercase tracking-wide text-ember">
                      Lesson {index + 1}
                    </span>
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="font-bold text-ink">{lesson.title}</h3>
                      <span className="rounded-md bg-slate-100 px-2 py-1 text-xs font-semibold capitalize text-slate-600">
                        {statusLabel(lesson.status)}
                      </span>
                    </div>
                    <p className="mt-2 text-sm leading-6 text-slate-600">{lesson.summary}</p>
                  </div>
                </div>
                <span className="btn-secondary shrink-0">
                  <Play size={16} aria-hidden="true" />
                  {lesson.status === "completed" ? "Review" : "Start lesson"}
                </span>
              </Link>
            ))}
          </div>
        </section>
      ) : (
        <EmptyState
          title="No lessons generated yet"
          body={
            project.data?.status === "generating"
              ? "The background job is preparing the learning path for this project."
              : "Lessons are generated automatically from your project goal. If none appear, regenerate the learning path; you do not need to add lessons manually."
          }
          action={
            project.data?.status === "generating" ? (
              <Link className="btn-secondary" to="/">
                Dashboard
              </Link>
            ) : (
              <button
                className="btn-primary"
                disabled={generateMutation.isPending}
                onClick={() => generateMutation.mutate()}
              >
                <Sparkles size={16} aria-hidden="true" />
                {generateMutation.isPending ? "Generating" : "Generate learning path"}
              </button>
            )
          }
        />
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md bg-white px-3 py-2">
      <div className="text-xs font-semibold text-slate-500">{label}</div>
      <div className="mt-1 text-base font-bold text-ink">{value.toLocaleString()}</div>
    </div>
  );
}
