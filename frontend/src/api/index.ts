import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1",
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("codepilgrim_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("codepilgrim_token");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export const authApi = {
  register: (data: { username: string; email: string; password: string; confirm_password: string; display_name: string; cognitive_style?: string; captcha_token: string }) =>
    api.post("/auth/register", data),
  login: (data: { username: string; password: string }) =>
    api.post("/auth/login", data),
  getMe: () => api.get("/auth/me"),
  getCaptchaChallenge: () => api.get("/auth/captcha/challenge"),
  verifyCaptcha: (data: { captcha_id: string; slider_x: number; slider_y: number }) =>
    api.post("/auth/captcha/verify", data),
};

export const knowledgeApi = {
  listPoints: (topic?: string) => api.get("/knowledge/points", { params: { topic } }),
  getPoint: (kpId: string) => api.get(`/knowledge/points/${kpId}`),
  listStates: () => api.get("/knowledge/states"),
  getLearningPath: () => api.get("/knowledge/path"),
  getNextKp: () => api.get("/knowledge/next"),
  getReviewPlan: () => api.get("/knowledge/review-plan"),
};

export const learningApi = {
  executeCode: (data: { code: string; kp_id?: string; language?: string }) =>
    api.post("/learning/execute", data),
  submitCode: (data: { code: string; kp_id: string; language?: string }) =>
    api.post("/learning/submit-code", data),
  submitQuiz: (data: { quiz_id: string; answer: string; response_time_ms?: number; hint_level_used?: number }) =>
    api.post("/learning/quiz", data),
  chatWithTutor: (data: { kp_id: string; message: string; session_id?: string }) =>
    api.post("/learning/chat", data),
  annotateCode: (data: { code: string; language?: string; kp_id?: string }) =>
    api.post("/learning/annotate-code", data),
  explainKnowledge: (data: { kp_id: string }) =>
    api.post("/learning/explain-knowledge", data),
  verifyMastery: (data: { kp_id: string; verification_level: string; code: string }) =>
    api.post("/learning/verify-mastery", data),
  getDailyPlan: () => api.get("/learning/daily-plan"),
  getCognitiveLoad: () => api.get("/learning/cognitive-load"),
};

export const courseApi = {
  listCourses: (language?: string) => api.get("/courses", { params: { language } }),
  getCourseDetail: (courseId: string) => api.get(`/courses/${courseId}`),
  getChapterDetail: (courseId: string, chapterId: string) => api.get(`/courses/${courseId}/chapters/${chapterId}`),
  enrollCourse: (courseId: string) => api.post("/courses/enroll", { course_id: courseId }),
  listEnrollments: () => api.get("/courses/enrollments"),
  updateChapterProgress: (chapterId: string, data: { status?: string; study_minutes?: number; mastery_score?: number; notes?: string }) =>
    api.put(`/courses/chapters/${chapterId}/progress`, data),
};

export const apiConfigApi = {
  getConfig: () => api.get("/api-config"),
  createConfig: (data: { provider: string; api_key: string; api_base_url?: string; model_name?: string }) => api.post("/api-config", data),
  updateConfig: (data: { provider?: string; api_key?: string; api_base_url?: string; model_name?: string; is_active?: boolean }) => api.put("/api-config", data),
  deleteConfig: () => api.delete("/api-config"),
  testConnection: (data?: { provider?: string; api_key?: string; api_base_url?: string; model_name?: string }) => api.post("/api-config/test", data),
  getUsage: () => api.get("/api-config/usage"),
};

export default api;
