import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { BookOpen, CheckCircle2, Clock, Play } from "lucide-react";
import { api } from "../api/client";
import { EmptyState, ErrorMessage, LoadingBlock } from "../components/Layout";

export default function ProjectDetailPage() {
  const { projectId } = useParams();
  const id = Number(projectId);
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

      {lessons.data?.length ? (
        <section className="grid gap-4">
          {lessons.data.map((lesson) => (
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
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="font-bold text-ink">{lesson.title}</h2>
                    <span className="rounded-md bg-slate-100 px-2 py-1 text-xs font-semibold capitalize text-slate-600">
                      {lesson.status}
                    </span>
                  </div>
                  <p className="mt-2 text-sm leading-6 text-slate-600">{lesson.summary}</p>
                </div>
              </div>
              <span className="btn-secondary shrink-0">
                <Play size={16} aria-hidden="true" />
                Open
              </span>
            </Link>
          ))}
        </section>
      ) : (
        <EmptyState
          title="Lessons are not ready yet"
          body={
            project.data?.status === "generating"
              ? "The background job is still preparing this project."
              : "No lessons exist for this project yet."
          }
          action={
            <Link className="btn-secondary" to="/">
              <Clock size={16} />
              Dashboard
            </Link>
          }
        />
      )}
    </div>
  );
}

