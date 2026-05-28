import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BookOpen, CheckCircle2, Play, Sparkles } from "lucide-react";
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
  const generateMutation = useMutation({
    mutationFn: () => api.generateProject(id),
    onSuccess: (response) => {
      queryClient.invalidateQueries({ queryKey: ["project", id] });
      queryClient.invalidateQueries({ queryKey: ["lessons", id] });
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
        <div className="mt-6">
          <div className="mb-2 flex items-center justify-between text-xs font-semibold text-slate-500">
            <span>Progress</span>
            <span>{project.data?.progress_percent ?? 0}%</span>
          </div>
          <div className="h-2 rounded-full bg-slate-100">
            <div
              className="h-2 rounded-full bg-teal"
              style={{ width: `${project.data?.progress_percent ?? 0}%` }}
            />
          </div>
        </div>
      </section>

      {lessons.error ? <ErrorMessage message={lessons.error.message} /> : null}
      {generateMutation.error ? <ErrorMessage message={generateMutation.error.message} /> : null}

      {lessons.data?.length ? (
        <section className="space-y-3">
          <div>
            <h2 className="text-lg font-bold text-ink">AI-generated learning path</h2>
            <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
              Each card is a lesson unit created from your project goal. Work through them in
              order: open a lesson, read the tutor notes, answer the check questions, and review
              anything you miss.
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
