import { FormEvent, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Brain, FileUp, Sparkles } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { ErrorMessage } from "../components/Layout";

const MAX_MATERIAL_FILE_BYTES = 8 * 1024 * 1024;

function formatFileSize(bytes: number) {
  return `${Math.round((bytes / 1024 / 1024) * 10) / 10} MB`;
}

export default function CreateProjectPage() {
  const [sourceType, setSourceType] = useState<"skill" | "material">("skill");
  const [title, setTitle] = useState("");
  const [goal, setGoal] = useState("");
  const [currentLevel, setCurrentLevel] = useState("");
  const [timeBudget, setTimeBudget] = useState(30);
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const navigate = useNavigate();
  const config = useQuery({ queryKey: ["app-config"], queryFn: api.appConfig });
  const maxMaterialFileBytes = config.data?.max_upload_bytes ?? MAX_MATERIAL_FILE_BYTES;

  const mutation = useMutation({
    mutationFn: async () => {
      const selectedFile = file;
      if (sourceType === "material") {
        if (!selectedFile) throw new Error("Choose a PDF, Markdown, or text file");
        if (selectedFile.size > maxMaterialFileBytes) {
          throw new Error(
            `File is ${formatFileSize(selectedFile.size)}. Maximum upload size is ${formatFileSize(
              maxMaterialFileBytes
            )}.`
          );
        }
        if (fileError) throw new Error(fileError);
      }
      if (sourceType === "material") {
        if (!selectedFile) throw new Error("Choose a PDF, Markdown, or text file");
        const created = await api.createMaterialProject({
          title,
          goal,
          current_level: currentLevel || null,
          time_budget_minutes: timeBudget,
          file: selectedFile
        });
        return { projectId: created.project.id, jobId: created.job_id };
      }
      const created = await api.createProject({
        title,
        goal,
        source_type: sourceType,
        current_level: currentLevel || null,
        time_budget_minutes: timeBudget
      });
      return { projectId: created.project.id, jobId: created.job_id };
    },
    onSuccess: ({ projectId, jobId }) => {
      navigate(jobId ? `/jobs/${jobId}?projectId=${projectId}` : `/projects/${projectId}`);
    }
  });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    mutation.mutate();
  }

  function handleFileChange(nextFile: File | null) {
    setFile(nextFile);
    if (nextFile && nextFile.size > maxMaterialFileBytes) {
      setFileError(
        `File is ${formatFileSize(nextFile.size)}. Maximum upload size is ${formatFileSize(
          maxMaterialFileBytes
        )}.`
      );
    } else {
      setFileError(null);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-ink">Create learning project</h1>
        <p className="mt-1 text-sm text-slate-600">
          Start from a skill goal or upload material for the tutor to structure.
        </p>
      </div>

      <form className="panel space-y-5" onSubmit={submit}>
        <div className="grid gap-3 sm:grid-cols-2">
          <button
            type="button"
            className={`focus-ring rounded-md border p-4 text-left transition ${
              sourceType === "skill"
                ? "border-teal bg-teal/5"
                : "border-line bg-white hover:border-teal"
            }`}
            onClick={() => setSourceType("skill")}
          >
            <Brain className="mb-3 text-teal" size={22} aria-hidden="true" />
            <span className="block font-bold text-ink">Skill goal</span>
            <span className="mt-1 block text-sm leading-6 text-slate-600">
              Ask the AI tutor to build a path from your target and current level.
            </span>
          </button>
          <button
            type="button"
            className={`focus-ring rounded-md border p-4 text-left transition ${
              sourceType === "material"
                ? "border-teal bg-teal/5"
                : "border-line bg-white hover:border-teal"
            }`}
            onClick={() => setSourceType("material")}
          >
            <FileUp className="mb-3 text-teal" size={22} aria-hidden="true" />
            <span className="block font-bold text-ink">Learning material</span>
            <span className="mt-1 block text-sm leading-6 text-slate-600">
              Upload PDF, Markdown, or text and turn it into a tutor learning path.
            </span>
          </button>
        </div>

        <label className="block">
          <span className="mb-1 block text-sm font-semibold text-ink">Title</span>
          <input
            className="field"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="Python foundations, product strategy, academic writing"
            required
          />
        </label>

        <label className="block">
          <span className="mb-1 block text-sm font-semibold text-ink">Goal</span>
          <textarea
            className="field min-h-28"
            value={goal}
            onChange={(event) => setGoal(event.target.value)}
            placeholder="Describe what you want to learn and why."
            required
          />
        </label>

        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block">
            <span className="mb-1 block text-sm font-semibold text-ink">Current level</span>
            <input
              className="field"
              value={currentLevel}
              onChange={(event) => setCurrentLevel(event.target.value)}
              placeholder="Beginner, intermediate, rusty"
            />
          </label>
          <label className="block">
            <span className="mb-1 block text-sm font-semibold text-ink">Minutes per session</span>
            <input
              className="field"
              type="number"
              min={5}
              max={600}
              value={timeBudget}
              onChange={(event) => setTimeBudget(Number(event.target.value))}
            />
          </label>
        </div>

        {sourceType === "material" ? (
          <div>
            <label className="block">
              <span className="mb-1 block text-sm font-semibold text-ink">Material file</span>
              <input
                className="field"
                type="file"
                accept=".pdf,.md,.markdown,.txt,text/plain,application/pdf"
                onChange={(event) => handleFileChange(event.target.files?.[0] ?? null)}
                required
              />
            </label>
            <p className="mt-2 text-xs leading-5 text-slate-500">
              Supported formats: PDF, Markdown, and plain text. Maximum upload size:{" "}
              {formatFileSize(maxMaterialFileBytes)}.
            </p>
            {fileError ? <div className="mt-3"><ErrorMessage message={fileError} /></div> : null}
          </div>
        ) : null}

        {mutation.error ? <ErrorMessage message={mutation.error.message} /> : null}

        <button className="btn-primary" disabled={mutation.isPending}>
          <Sparkles size={16} aria-hidden="true" />
          {mutation.isPending ? "Generating" : "Create and generate"}
        </button>
      </form>
    </div>
  );
}
