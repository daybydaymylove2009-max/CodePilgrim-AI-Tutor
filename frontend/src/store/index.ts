import { create } from "zustand";
import type { User, LearningPath, KnowledgeState, DailyPlan } from "../types";
import { authApi, knowledgeApi, learningApi } from "../api";

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (data: { username: string; email: string; password: string; display_name: string; cognitive_style?: string }) => Promise<void>;
  logout: () => void;
  loadUser: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: localStorage.getItem("codepilgrim_token"),
  isAuthenticated: !!localStorage.getItem("codepilgrim_token"),

  login: async (username, password) => {
    const { data } = await authApi.login({ username, password });
    localStorage.setItem("codepilgrim_token", data.access_token);
    set({ user: data.user, token: data.access_token, isAuthenticated: true });
  },

  register: async (userData) => {
    const { data } = await authApi.register(userData);
    localStorage.setItem("codepilgrim_token", data.access_token);
    set({ user: data.user, token: data.access_token, isAuthenticated: true });
  },

  logout: () => {
    localStorage.removeItem("codepilgrim_token");
    set({ user: null, token: null, isAuthenticated: false });
  },

  loadUser: async () => {
    try {
      const { data } = await authApi.getMe();
      set({ user: data, isAuthenticated: true });
    } catch {
      localStorage.removeItem("codepilgrim_token");
      set({ user: null, token: null, isAuthenticated: false });
    }
  },
}));

interface LearningState {
  learningPath: LearningPath | null;
  knowledgeStates: KnowledgeState[];
  dailyPlan: DailyPlan | null;
  currentKpId: string | null;
  cognitiveLoad: { load_level: string; message: string } | null;
  loadLearningPath: () => Promise<void>;
  loadKnowledgeStates: () => Promise<void>;
  loadDailyPlan: () => Promise<void>;
  loadCognitiveLoad: () => Promise<void>;
  setCurrentKpId: (kpId: string) => void;
}

export const useLearningStore = create<LearningState>((set) => ({
  learningPath: null,
  knowledgeStates: [],
  dailyPlan: null,
  currentKpId: null,
  cognitiveLoad: null,

  loadLearningPath: async () => {
    const { data } = await knowledgeApi.getLearningPath();
    set({ learningPath: data, currentKpId: data.current_kp_id });
  },

  loadKnowledgeStates: async () => {
    const { data } = await knowledgeApi.listStates();
    set({ knowledgeStates: data });
  },

  loadDailyPlan: async () => {
    const { data } = await learningApi.getDailyPlan();
    set({ dailyPlan: data });
  },

  loadCognitiveLoad: async () => {
    const { data } = await learningApi.getCognitiveLoad();
    set({ cognitiveLoad: data });
  },

  setCurrentKpId: (kpId) => set({ currentKpId: kpId }),
}));

interface ChatState {
  messages: { role: string; content: string }[];
  ercfStage: string;
  personaStage: string;
  hintLevel: number | null;
  isLoading: boolean;
  sendMessage: (kpId: string, message: string) => Promise<void>;
  clearMessages: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  ercfStage: "R1",
  personaStage: "guide",
  hintLevel: null,
  isLoading: false,

  sendMessage: async (kpId, message) => {
    set((state) => ({ messages: [...state.messages, { role: "user", content: message }], isLoading: true }));
    try {
      const { data } = await learningApi.chatWithTutor({ kp_id: kpId, message });
      set((state) => ({
        messages: [...state.messages, { role: "assistant", content: data.assistant_message }],
        ercfStage: data.ercf_stage,
        personaStage: data.persona_stage,
        hintLevel: data.hint_level,
        isLoading: false,
      }));
    } catch {
      set((state) => ({
        messages: [...state.messages, { role: "assistant", content: "抱歉，出了点问题，请重试。" }],
        isLoading: false,
      }));
    }
  },

  clearMessages: () => set({ messages: [], ercfStage: "R1", personaStage: "guide", hintLevel: null }),
}));
