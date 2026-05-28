import type {
  AnswerResult,
  AppConfig,
  Job,
  Lesson,
  MaterialUploadResponse,
  Mistake,
  Project,
  ProjectCreateResponse,
  QuizItem,
  ReviewTask,
  User
} from "./types";

type JsonBody = Record<string, unknown>;

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  const isFormData = options.body instanceof FormData;
  if (!isFormData && options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(`/api${path}`, {
    ...options,
    headers,
    credentials: "include"
  });
  if (!response.ok) {
    let message = response.statusText;
    try {
      const payload = await response.json();
      message = payload.detail || message;
    } catch {
      // Use status text when the response is not JSON.
    }
    throw new Error(message);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

function jsonBody(body: JsonBody): string {
  return JSON.stringify(body);
}

export const api = {
  appConfig() {
    return apiFetch<AppConfig>("/config");
  },
  register(email: string, password: string) {
    return apiFetch<User>("/auth/register", {
      method: "POST",
      body: jsonBody({ email, password })
    });
  },
  login(email: string, password: string) {
    return apiFetch<User>("/auth/login", {
      method: "POST",
      body: jsonBody({ email, password })
    });
  },
  logout() {
    return apiFetch<{ ok: boolean }>("/auth/logout", { method: "POST" });
  },
  me() {
    return apiFetch<User>("/auth/me");
  },
  projects() {
    return apiFetch<Project[]>("/projects");
  },
  project(id: number) {
    return apiFetch<Project>(`/projects/${id}`);
  },
  createProject(body: {
    title: string;
    goal: string;
    source_type: "skill" | "material";
    current_level?: string | null;
    time_budget_minutes?: number | null;
  }) {
    return apiFetch<ProjectCreateResponse>("/projects", {
      method: "POST",
      body: jsonBody(body)
    });
  },
  generateProject(projectId: number) {
    return apiFetch<ProjectCreateResponse>(`/projects/${projectId}/generate`, {
      method: "POST"
    });
  },
  uploadMaterial(projectId: number, file: File) {
    const formData = new FormData();
    formData.append("file", file);
    return apiFetch<MaterialUploadResponse>(`/projects/${projectId}/materials`, {
      method: "POST",
      body: formData
    });
  },
  job(id: number) {
    return apiFetch<Job>(`/jobs/${id}`);
  },
  lessons(projectId: number) {
    return apiFetch<Lesson[]>(`/projects/${projectId}/lessons`);
  },
  lesson(id: number) {
    return apiFetch<Lesson>(`/lessons/${id}`);
  },
  completeLesson(id: number) {
    return apiFetch<Lesson>(`/lessons/${id}/complete`, { method: "POST" });
  },
  quiz(lessonId: number) {
    return apiFetch<QuizItem[]>(`/lessons/${lessonId}/quiz`);
  },
  answerQuiz(quizItemId: number, answer: string) {
    return apiFetch<AnswerResult>(`/quiz-items/${quizItemId}/answer`, {
      method: "POST",
      body: jsonBody({ answer })
    });
  },
  reviewsToday() {
    return apiFetch<ReviewTask[]>("/reviews/today");
  },
  submitReview(reviewId: number, answer: string) {
    return apiFetch<AnswerResult>(`/reviews/${reviewId}/submit`, {
      method: "POST",
      body: jsonBody({ answer })
    });
  },
  mistakes() {
    return apiFetch<Mistake[]>("/mistakes");
  }
};
