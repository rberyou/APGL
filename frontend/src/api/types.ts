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
  status: "pending" | "processing" | "completed" | "failed" | "interrupted";
  error: string | null;
  stage_key: string | null;
  stage_label: string | null;
  progress_percent: number;
  message: string;
  error_stage: string | null;
  retry_of_job_id: number | null;
  resumed_from_job_id: number | null;
  stages?: JobStage[];
  created_at: string;
  updated_at: string;
};

export type JobStage = {
  id: number;
  job_id: number;
  project_id: number;
  stage_key: string;
  label: string;
  status: "pending" | "running" | "completed" | "skipped" | "failed";
  order_index: number;
  message: string;
  details_json: string;
  error: string | null;
  is_retryable: boolean;
  started_at: string | null;
  completed_at: string | null;
  updated_at: string;
};

export type MaterialUploadResponse = {
  material: {
    id: number;
    project_id: number;
    filename: string;
    content_type: string;
    status: string;
    page_count: number;
    text_page_count: number;
    character_count: number;
    chunk_count: number;
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
  knowledge_points: KnowledgePoint[];
  mastery: number;
};

export type KnowledgePoint = {
  id: number;
  client_key: string | null;
  name: string;
  explanation: string;
  difficulty: string;
  estimated_weight: number;
  source_locator: string | null;
  mastery: number;
};

export type LessonStep = {
  id: number;
  lesson_id: number;
  project_id: number;
  step_type: string;
  title: string;
  body: string;
  order_index: number;
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

export type MaterialStatus = {
  project_id: number;
  material_id: number | null;
  filename: string | null;
  status: string;
  page_count: number;
  text_page_count: number;
  character_count: number;
  chunk_count: number;
  readable: boolean;
  message: string;
};

export type KnowledgeMap = {
  project_id: number;
  nodes: Array<{
    id: number;
    client_key: string | null;
    name: string;
    explanation: string;
    difficulty: string;
    estimated_weight: number;
    source_locator: string | null;
    mastery: number;
    lesson_ids: number[];
    lesson_titles: string[];
  }>;
  edges: Array<{
    id: number;
    source_id: number;
    target_id: number;
    relation_type: string;
  }>;
};

export type ProjectTracker = {
  project_id: number;
  mastery: number;
  progress_percent: number;
  mastered_topics: string[];
  learning_gaps: Array<{
    id: number | null;
    title: string;
    severity: string;
    status: string;
    evidence: string;
  }>;
  next_plan: string;
  last_session_id: number | null;
  updated_at: string;
};

export type StudySession = {
  id: number;
  project_id: number;
  user_id: number;
  lesson_id: number | null;
  status: string;
  focus: string;
  summary: string | null;
  next_plan: string | null;
  started_at: string;
  ended_at: string | null;
};

export type TutorCitation = {
  chunk_id: number | null;
  title: string;
  locator: string | null;
  excerpt: string;
};

export type TutorMessage = {
  id: number;
  session_id: number;
  project_id: number;
  role: "assistant" | "user";
  content: string;
  citations: TutorCitation[];
  created_at: string;
};

export type AssessmentTurn = {
  id: number;
  assessment_id: number;
  project_id: number;
  lesson_id: number;
  knowledge_point_id: number | null;
  quiz_item_id: number | null;
  status: "asked" | "answered" | "skipped";
  question: string;
  user_answer: string | null;
  feedback: string | null;
  score: number | null;
  mastery_delta: number | null;
  missing_concepts: string[];
  next_action: string | null;
  citations: TutorCitation[];
  created_at: string;
  answered_at: string | null;
};

export type AssessmentSession = {
  id: number;
  project_id: number;
  lesson_id: number;
  user_id: number;
  status: "active" | "completed";
  mode: string;
  summary: string | null;
  lesson_mastery: number;
  turns_answered: number;
  current_turn: AssessmentTurn | null;
  turns: AssessmentTurn[];
  started_at: string;
  ended_at: string | null;
  updated_at: string;
};
