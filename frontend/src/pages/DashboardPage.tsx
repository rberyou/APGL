import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { BookOpen, Clock, Plus, RotateCcw, TriangleAlert } from "lucide-react";
import { api } from "../api/client";
import { EmptyState, ErrorMessage, LoadingBlock } from "../components/Layout";

export default function DashboardPage() {
  const projects = useQuery({ queryKey: ["projects"], queryFn: api.projects });
  const reviews = useQuery({ queryKey: ["reviews", "today"], queryFn: api.reviewsToday });
  const mistakes = useQuery({ queryKey: ["mistakes"], queryFn: api.mistakes });

  if (projects.isLoading) return <LoadingBlock label="Loading dashboard" />;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-ink">Today</h1>
          <p className="mt-1 text-sm text-slate-600">
            Pick up a lesson, clear a review, or start a new guided learning project.
          </p>
        </div>
        <Link className="btn-primary" to="/projects/new">
          <Plus size={16} aria-hidden="true" />
          New project
        </Link>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <MetricCard
          icon={<BookOpen size={20} />}
          label="Active projects"
          value={projects.data?.length ?? 0}
        />
        <MetricCard
          icon={<RotateCcw size={20} />}
          label="Due reviews"
          value={reviews.data?.length ?? 0}
        />
        <MetricCard
          icon={<TriangleAlert size={20} />}
          label="Open mistakes"
          value={mistakes.data?.length ?? 0}
        />
      </div>

      {projects.error ? <ErrorMessage message={projects.error.message} /> : null}

      {projects.data?.length ? (
        <section className="grid gap-4 lg:grid-cols-2">
          {projects.data.map((project) => (
            <Link
              key={project.id}
              to={`/projects/${project.id}`}
              className="panel block transition hover:border-teal"
            >
              <div className="flex items-start justify-between gap-4">
                <div>
                  <span className="text-xs font-bold uppercase tracking-wide text-ember">
                    {project.source_type}
                  </span>
                  <h2 className="mt-2 text-lg font-bold text-ink">{project.title}</h2>
                  <p className="mt-2 line-clamp-2 text-sm leading-6 text-slate-600">
                    {project.goal}
                  </p>
                </div>
                <span className="rounded-md border border-line px-2 py-1 text-xs font-semibold text-slate-600">
                  {project.status}
                </span>
              </div>
              <div className="mt-5">
                <div className="mb-2 flex items-center justify-between text-xs font-semibold text-slate-500">
                  <span>Progress</span>
                  <span>{project.progress_percent}%</span>
                </div>
                <div className="h-2 rounded-full bg-slate-100">
                  <div
                    className="h-2 rounded-full bg-teal"
                    style={{ width: `${project.progress_percent}%` }}
                  />
                </div>
              </div>
            </Link>
          ))}
        </section>
      ) : (
        <EmptyState
          title="No learning projects yet"
          body="Create a skill project or upload learning material to let the AI tutor build your first study path."
          action={
            <Link className="btn-primary" to="/projects/new">
              <Plus size={16} />
              Create project
            </Link>
          }
        />
      )}
    </div>
  );
}

function MetricCard({
  icon,
  label,
  value
}: {
  icon: ReactNode;
  label: string;
  value: number;
}) {
  return (
    <div className="panel">
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold text-slate-500">{label}</span>
        <span className="text-teal">{icon}</span>
      </div>
      <div className="mt-4 flex items-end gap-2">
        <span className="text-3xl font-bold text-ink">{value}</span>
        <Clock className="mb-1 text-slate-400" size={16} aria-hidden="true" />
      </div>
    </div>
  );
}
