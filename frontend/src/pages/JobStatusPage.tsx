import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { CheckCircle2, Loader2, XCircle } from "lucide-react";
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
          The tutor is preparing lessons, knowledge points, and quiz prompts.
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

