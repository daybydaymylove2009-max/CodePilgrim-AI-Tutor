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
  register: (data: { username: string; email: string; password: string; display_name: string; cognitive_style?: string }) =>
    api.post("/auth/register", data),
  login: (data: { username: string; password: string }) =>
    api.post("/auth/login", data),
  getMe: () => api.get("/auth/me"),
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
  executeCode: (data: { code: string; kp_id: string; language?: string }) =>
    api.post("/learning/execute", data),
  submitCode: (data: { code: string; kp_id: string; language?: string }) =>
    api.post("/learning/submit-code", data),
  submitQuiz: (data: { quiz_id: string; answer: string; response_time_ms?: number; hint_level_used?: number }) =>
    api.post("/learning/quiz", data),
  chatWithTutor: (data: { kp_id: string; message: string; session_id?: string }) =>
    api.post("/learning/chat", data),
  verifyMastery: (data: { kp_id: string; verification_level: string; code: string }) =>
    api.post("/learning/verify-mastery", data),
  getDailyPlan: () => api.get("/learning/daily-plan"),
  getCognitiveLoad: () => api.get("/learning/cognitive-load"),
};

export default api;
