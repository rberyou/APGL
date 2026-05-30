import { useEffect } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { CheckCircle2, Circle, Loader2, RotateCw, XCircle } from "lucide-react";
import { api } from "../api/client";
import { ErrorMessage, LoadingBlock } from "../components/Layout";

export default function JobStatusPage() {
  const { jobId } = useParams();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const id = Number(jobId);
  const projectId = Number(params.get("projectId"));
  const job = useQuery({
    queryKey: ["job", id],
    queryFn: () => api.job(id),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "completed" || status === "failed" ? false : 1500;
    },
    enabled: Number.isFinite(id)
  });
  const continueMutation = useMutation({
    mutationFn: async () => {
      if (!job.data) throw new Error("Job is not loaded yet");
      if (job.data.status === "failed") return api.retryJob(job.data.id);
      return api.resumeJob(job.data.id);
    },
    onSuccess: (nextJob) => {
      navigate(`/jobs/${nextJob.id}?projectId=${nextJob.project_id}`);
    }
  });

  useEffect(() => {
    if (job.data?.status === "completed" && projectId) {
      const timer = window.setTimeout(() => navigate(`/projects/${projectId}`), 900);
      return () => window.clearTimeout(timer);
    }
    return undefined;
  }, [job.data?.status, navigate, projectId]);

  if (job.isLoading) return <LoadingBlock label="Checking generation job" />;

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-ink">Generation status</h1>
        <p className="mt-1 text-sm text-slate-600">
          The tutor is building the project brief, knowledge map, lesson path, and first lesson.
        </p>
      </div>
      {job.error ? <ErrorMessage message={job.error.message} /> : null}
      {job.data ? (
        <section className="panel">
          <div className="flex items-center gap-3">
            {job.data.status === "completed" ? (
              <CheckCircle2 className="text-teal" size={28} aria-hidden="true" />
            ) : job.data.status === "failed" ? (
              <XCircle className="text-red-600" size={28} aria-hidden="true" />
            ) : (
              <Loader2 className="animate-spin text-ember" size={28} aria-hidden="true" />
            )}
            <div>
              <h2 className="text-lg font-bold capitalize text-ink">{job.data.status}</h2>
              <p className="text-sm text-slate-600">{job.data.job_type}</p>
            </div>
          </div>
          {job.data.error ? <ErrorMessage message={job.data.error} /> : null}
          <div className="mt-5">
            <div className="mb-2 flex items-center justify-between text-xs font-semibold text-slate-500">
              <span>{job.data.stage_label || "Generation"}</span>
              <span>{job.data.progress_percent}%</span>
            </div>
            <div className="h-2 rounded-full bg-slate-100">
              <div className="h-2 rounded-full bg-teal" style={{ width: `${job.data.progress_percent}%` }} />
            </div>
          </div>
          {job.data.stages?.length ? (
            <div className="mt-6 space-y-3">
              {job.data.stages.map((stage) => (
                <div key={stage.id} className="flex gap-3 rounded-md border border-line p-3">
                  <StageIcon status={stage.status} />
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <h3 className="text-sm font-bold text-ink">{stage.label}</h3>
                      <span className="text-xs font-semibold capitalize text-slate-500">
                        {stage.status}
                      </span>
                    </div>
                    <p className="mt-1 text-sm leading-5 text-slate-600">
                      {stage.error || stage.message}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : null}
          {job.data.status === "failed" || job.data.status === "interrupted" ? (
            <div className="mt-5 rounded-md border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-900">
              <p>
                {job.data.status === "failed"
                  ? `Generation failed while working on ${job.data.stage_label || job.data.error_stage || "a stage"}. APGL will reuse saved artifacts where possible.`
                  : `Generation was interrupted while working on ${job.data.stage_label || "a stage"}. APGL will continue from the last saved stage.`}
              </p>
              <button
                className="btn-primary mt-3"
                disabled={continueMutation.isPending}
                onClick={() => continueMutation.mutate()}
              >
                <RotateCw size={16} aria-hidden="true" />
                {continueMutation.isPending ? "Continuing" : "Continue generation"}
              </button>
              {continueMutation.error ? <div className="mt-3"><ErrorMessage message={continueMutation.error.message} /></div> : null}
            </div>
          ) : null}
          <div className="mt-5 flex flex-wrap gap-3">
            {projectId ? (
              <Link className="btn-primary" to={`/projects/${projectId}`}>
                Open project
              </Link>
            ) : null}
            <Link className="btn-secondary" to="/">
              Dashboard
            </Link>
          </div>
        </section>
      ) : null}
    </div>
  );
}

function StageIcon({ status }: { status: string }) {
  if (status === "completed") return <CheckCircle2 className="mt-0.5 text-teal" size={18} aria-hidden="true" />;
  if (status === "failed") return <XCircle className="mt-0.5 text-red-600" size={18} aria-hidden="true" />;
  if (status === "running") return <Loader2 className="mt-0.5 animate-spin text-ember" size={18} aria-hidden="true" />;
  return <Circle className="mt-0.5 text-slate-300" size={18} aria-hidden="true" />;
}

