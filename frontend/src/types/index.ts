export interface User {
  id: string;
  username: string;
  email: string;
  display_name: string;
  avatar_url: string | null;
  role: string;
  cognitive_style: string;
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface KnowledgePoint {
  id: string;
  title: string;
  description: string | null;
  topic: string;
  difficulty: number;
  irt_b_param: number | null;
  prerequisites: Record<string, unknown>[] | null;
  learning_objectives: string[] | null;
  created_at: string;
}

export interface KnowledgeState {
  id: string;
  kp_id: string;
  bkt_p_know: number;
  mastery_level: string;
  independent_completion_rate: number;
  deformation_pass_rate: number;
  total_attempts: number;
  correct_attempts: number;
  last_reviewed_at: string | null;
  next_review_at: string | null;
  review_interval_days: number;
  persona_stage: string;
  updated_at: string;
}

export interface LearningPathNode {
  kp_id: string;
  title: string;
  difficulty: number;
  mastery_level: string;
  bkt_p_know: number;
  is_unlocked: boolean;
  is_current: boolean;
}

export interface LearningPath {
  nodes: LearningPathNode[];
  total_kps: number;
  mastered_count: number;
  current_kp_id: string | null;
}

export interface ExecutionResult {
  success: boolean;
  stdout: string;
  stderr: string;
  exit_code: number;
  execution_time_ms: number;
  memory_used_mb: number;
  error_type: string | null;
  error_message: string | null;
}

export interface AIChatResponse {
  session_id: string;
  assistant_message: string;
  ercf_stage: string;
  persona_stage: string;
  hint_level: number | null;
  intervention: Record<string, unknown> | null;
}

export interface QuizAttemptResponse {
  id: string;
  quiz_id: string;
  is_correct: boolean;
  bkt_p_before: number;
  bkt_p_after: number;
  explanation: string | null;
}

export interface DailyPlan {
  review_items: { kp_id: string; priority: string }[];
  new_items: { kp_id: string; priority: string }[];
  challenge_items: { kp_id: string; priority: string }[];
}

export interface MasteryVerificationResult {
  verification_level: string;
  passed: boolean;
  description: string;
  bkt_p_know: number;
  independent_completion_rate: number;
  deformation_pass_rate: number;
  execution_success: boolean;
}

export interface CognitiveLoadAssessment {
  load_level: string;
  actions: string[];
  message: string;
  suggestions: string[];
}
