export type User = {
  id: number;
  email: string;
};

export type Project = {
  id: number;
  title: string;
  goal: string;
  source_type: "skill" | "material";
  current_level: string | null;
  time_budget_minutes: number | null;
  status: string;
  progress_percent: number;
  created_at: string;
  updated_at: string;
};

export type ProjectCreateResponse = {
  project: Project;
  job_id: number | null;
};

export type Job = {
  id: number;
  project_id: number;
  material_id: number | null;
  job_type: string;
  status: "pending" | "processing" | "completed" | "failed";
  error: string | null;
  created_at: string;
  updated_at: string;
};

export type MaterialUploadResponse = {
  material: {
    id: number;
    project_id: number;
    filename: string;
    content_type: string;
    status: string;
    created_at: string;
  };
  job_id: number;
};

export type Lesson = {
  id: number;
  project_id: number;
  title: string;
  summary: string;
  content: string;
  order_index: number;
  status: string;
};

export type QuizItem = {
  id: number;
  lesson_id: number;
  question_type: string;
  prompt: string;
  options_json: string | null;
};

export type AnswerResult = {
  is_correct: boolean;
  feedback: string;
  explanation: string;
  review_task_id: number | null;
};

export type ReviewTask = {
  id: number;
  quiz_item_id: number;
  prompt: string;
  due_at: string;
  status: string;
};

export type Mistake = {
  id: number;
  quiz_item_id: number;
  prompt: string;
  user_answer: string;
  reason: string;
  status: string;
  created_at: string;
};

export type AppConfig = {
  max_upload_bytes: number;
};
