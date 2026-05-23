import { useState, useRef, useEffect, useCallback } from "react";
import Editor from "@monaco-editor/react";
import { learningApi, courseApi } from "../../api";
import { useLearningStore, useChatStore } from "../../store";
import type { ExecutionResult } from "../../types";
import type { ExecutionResponse, DispatchDecision, BackendStatus, SupportedLanguage } from "../../execution";
import { executionDispatcher, isFrontendLanguage } from "../../execution";
import {
  Play, Send, RotateCcw, Lightbulb, AlertCircle, Cpu, Wifi, Server,
  Loader2, BookOpen, MessageSquare, ChevronRight, ChevronDown, Library,
  Terminal, History, XCircle, AlertTriangle, ChevronUp, StopCircle, Keyboard,
  Clock, HardDrive, Zap,
} from "lucide-react";

const PERSONA_LABELS: Record<string, string> = { guide: "引路者", collaborator: "协作者", peer: "同伴", launcher: "发射者" };
const ERCF_LABELS: Record<string, string> = { R1: "问题解析", R2: "概念识别", R3: "逻辑分解", R4: "错误诊断", R5: "引导提示" };
const BACKEND_ICONS: Record<string, React.ReactNode> = { wasm: <Cpu size={12} />, agent: <Wifi size={12} />, server: <Server size={12} /> };
const BACKEND_LABELS: Record<string, string> = { wasm: "浏览器 WASM", agent: "本地 Agent", server: "服务端" };

const LANGUAGE_OPTIONS: { value: SupportedLanguage; label: string; monacoLang: string; defaultCode: string }[] = [
  { value: "python", label: "Python", monacoLang: "python", defaultCode: "# 在这里编写你的代码\nprint('Hello, CodePilgrim!')\n" },
  { value: "javascript", label: "JavaScript", monacoLang: "javascript", defaultCode: "// 在这里编写你的代码\nconsole.log('Hello, CodePilgrim!');\n" },
  { value: "rust", label: "Rust", monacoLang: "rust", defaultCode: "fn main() {\n    println!(\"Hello, CodePilgrim!\");\n}\n" },
  { value: "react", label: "React", monacoLang: "javascript", defaultCode: "function App() {\n  const [count, setCount] = React.useState(0);\n  return (\n    <div style={{padding: 20, fontFamily: 'sans-serif'}}>\n      <h1>React 计数器</h1>\n      <p>当前计数: {count}</p>\n      <button onClick={() => setCount(count + 1)}>+1</button>\n      <button onClick={() => setCount(0)}>重置</button>\n    </div>\n  );\n}\n\nReactDOM.createRoot(document.getElementById('root')).render(<App />);\n" },
  { value: "vue", label: "Vue", monacoLang: "javascript", defaultCode: "createApp({\n  setup() {\n    const count = ref(0);\n    return { count };\n  },\n  template: `\n    <div style=\"padding:20px;font-family:sans-serif\">\n      <h1>Vue 计数器</h1>\n      <p>当前计数: {{ count }}</p>\n      <button @click=\"count++\">+1</button>\n      <button @click=\"count = 0\">重置</button>\n    </div>\n  `\n}).mount('#app');\n" },
];

const LANGUAGE_COURSE_MAP: Record<string, string> = {
  python: "python", javascript: "javascript", rust: "rust", react: "react", vue: "vue",
};

interface StructuredError {
  error_type: string;
  message: string;
  line_number: number | null;
  column: number | null;
  suggestion: string | null;
}

interface ExecHistoryEntry {
  id: string;
  timestamp: number;
  language: string;
  code: string;
  success: boolean;
  exitCode: number;
  executionTimeMs: number;
  peakMemoryMb: number | null;
  error: StructuredError | null;
  stdout: string;
  stderr: string;
}

type OutputTab = "output" | "problems" | "terminal" | "history";

interface CourseInfo {
  id: string; title: string; subtitle: string | null; author: string | null;
  edition: string | null; publisher: string | null; total_chapters: number;
  estimated_hours: number | null; sort_order: number;
}

interface ChapterInfo {
  id: string; course_id: string; part_number: number; part_title: string | null;
  chapter_number: number; chapter_title: string; estimated_minutes: number | null;
  difficulty: number; kp_ids: string[] | null; learning_objectives: string[] | null;
  key_concepts: string[] | null;
}

interface ChapterDetail {
  chapter: ChapterInfo;
  knowledge_points: {
    id: string; title: string; description: string | null; difficulty: number;
    learning_objectives: string[] | null; code_examples: string[] | null;
    mastery_level: string; bkt_p_know: number;
  }[];
  progress: { status: string; study_minutes: number; mastery_score: number } | null;
}

function loadHistory(): ExecHistoryEntry[] {
  try {
    const raw = localStorage.getItem("codepilgrim_exec_history");
    return raw ? JSON.parse(raw) : [];
  } catch { return []; }
}

function saveHistory(entries: ExecHistoryEntry[]) {
  localStorage.setItem("codepilgrim_exec_history", JSON.stringify(entries.slice(-50)));
}

export default function CodeWorkspace() {
  const [language, setLanguage] = useState<SupportedLanguage>("python");
  const [code, setCode] = useState(LANGUAGE_OPTIONS[0].defaultCode);
  const [execResult, setExecResult] = useState<ExecutionResult | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [runError, setRunError] = useState("");
  const [lastBackend, setLastBackend] = useState<DispatchDecision | null>(null);
  const [backendStatuses, setBackendStatuses] = useState<BackendStatus[]>([]);
  const [wasmProgress, setWasmProgress] = useState(0);
  const [previewHtml, setPreviewHtml] = useState<string | null>(null);
  const [annotatedCode, setAnnotatedCode] = useState<string | null>(null);
  const [isAnnotating, setIsAnnotating] = useState(false);
  const [showAnnotated, setShowAnnotated] = useState(false);
  const { currentKpId, setCurrentKpId, loadLearningPath, loadKnowledgeStates } = useLearningStore();
  const { ercfStage, personaStage, hintLevel, sendMessage, messages, isLoading, clearMessages } = useChatStore();
  const [chatInput, setChatInput] = useState("");
  const chatEndRef = useRef<HTMLDivElement>(null);
  const previewRef = useRef<HTMLIFrameElement>(null);
  const prevKpIdRef = useRef<string | null>(null);
  const editorRef = useRef<any>(null);

  const [outputTab, setOutputTab] = useState<OutputTab>("output");
  const [stdinInput, setStdinInput] = useState("");
  const [showStdin, setShowStdin] = useState(false);
  const [execHistory, setExecHistory] = useState<ExecHistoryEntry[]>(loadHistory);
  const [structuredError, setStructuredError] = useState<StructuredError | null>(null);
  const [securityViolations, setSecurityViolations] = useState<string[]>([]);
  const [peakMemoryMb, setPeakMemoryMb] = useState<number | null>(null);

  const [courses, setCourses] = useState<CourseInfo[]>([]);
  const [selectedCourse, setSelectedCourse] = useState<string | null>(null);
  const [chapters, setChapters] = useState<ChapterInfo[]>([]);
  const [selectedChapter, setSelectedChapter] = useState<ChapterDetail | null>(null);
  const [expandedParts, setExpandedParts] = useState<Set<number>>(new Set());
  const [coursePanelOpen, setCoursePanelOpen] = useState(true);
  const [coursesLoading, setCoursesLoading] = useState(false);

  useEffect(() => { loadCoursesForLanguage(language); }, []);

  useEffect(() => {
    if (language === "python" && /\binput\s*\(/.test(code)) {
      setShowStdin(true);
    }
  }, [code, language]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        if (!isRunning) handleRun();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [isRunning, code, language, currentKpId]);

  const loadCoursesForLanguage = async (lang: SupportedLanguage) => {
    const courseLang = LANGUAGE_COURSE_MAP[lang] || lang;
    setCoursesLoading(true);
    try {
      const { data } = await courseApi.listCourses(courseLang);
      setCourses(data);
      if (data.length > 0) { await selectCourse(data[0].id); }
      else { setChapters([]); setSelectedChapter(null); setSelectedCourse(null); }
    } catch { setCourses([]); setChapters([]); setSelectedCourse(null); }
    finally { setCoursesLoading(false); }
  };

  const selectCourse = async (courseId: string) => {
    setSelectedCourse(courseId); setSelectedChapter(null);
    try {
      const { data } = await courseApi.getCourseDetail(courseId);
      setChapters(data.chapters);
      setExpandedParts(new Set(data.chapters.map((ch: ChapterInfo) => ch.part_number)));
      try { await courseApi.enrollCourse(courseId); } catch {}
    } catch { setChapters([]); }
  };

  const selectChapter = async (chapter: ChapterInfo) => {
    if (!selectedCourse) return;
    try {
      const { data } = await courseApi.getChapterDetail(selectedCourse, chapter.id);
      setSelectedChapter(data);
      if (data.knowledge_points.length > 0) setCurrentKpId(data.knowledge_points[0].id);
      try { await courseApi.updateChapterProgress(chapter.id, { status: "in_progress" }); } catch {}
    } catch { console.error("Failed to load chapter detail"); }
  };

  const togglePart = (partNum: number) => {
    setExpandedParts(prev => { const next = new Set(prev); if (next.has(partNum)) next.delete(partNum); else next.add(partNum); return next; });
  };

  const difficultyStars = (d: number) => "★".repeat(d) + "☆".repeat(5 - d);

  const groupedChapters = chapters.reduce<Record<number, { part_title: string; items: ChapterInfo[] }>>((acc, ch) => {
    if (!acc[ch.part_number]) acc[ch.part_number] = { part_title: ch.part_title || `Part ${ch.part_number}`, items: [] };
    acc[ch.part_number].items.push(ch);
    return acc;
  }, {});

  useEffect(() => {
    const update = () => setBackendStatuses(executionDispatcher.getBackendStatuses());
    update();
    const interval = setInterval(update, 2000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    let cancelled = false;
    executionDispatcher.initWasm((p) => { if (!cancelled) setWasmProgress(p); })
      .then(() => { if (!cancelled) { setWasmProgress(100); setBackendStatuses(executionDispatcher.getBackendStatuses()); } })
      .catch(() => {});
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (currentKpId && currentKpId !== prevKpIdRef.current) {
      prevKpIdRef.current = currentKpId;
      clearMessages();
      requestKnowledgeExplanation(currentKpId);
    }
  }, [currentKpId]);

  const requestKnowledgeExplanation = async (kpId: string) => {
    try {
      const explainRes = await learningApi.explainKnowledge({ kp_id: kpId });
      const data = explainRes.data;
      const parts: string[] = [];
      parts.push(`📖 **${data.title}**`); parts.push("");
      if (data.explanation) { parts.push(data.explanation); parts.push(""); }
      if (data.key_points?.length > 0) { parts.push("🔑 核心要点："); data.key_points.forEach((p: string) => parts.push(`  • ${p}`)); parts.push(""); }
      if (data.code_example) { parts.push("💡 代码示例："); parts.push("```"); parts.push(data.code_example); parts.push("```"); parts.push(""); }
      if (data.common_mistakes?.length > 0) { parts.push("⚠️ 常见错误："); data.common_mistakes.forEach((m: string) => parts.push(`  • ${m}`)); }
      const isDbFallback = !data.key_points?.length && !data.code_example;
      if (isDbFallback) { parts.push(""); parts.push("💡 **提示**：配置个人 AI API 密钥后，可获得更详细的专业级智能解说。前往「API 设置」进行配置。"); }
      useChatStore.setState((state) => ({ messages: [...state.messages, { role: "assistant", content: parts.join("\n") }] }));
      chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
    } catch (err: any) {
      const errMsg = err?.response?.data?.detail || err?.message || "未知错误";
      useChatStore.setState((state) => ({ messages: [...state.messages, { role: "assistant", content: `📖 知识点解说加载遇到问题（${errMsg}）。\n\n当前使用数据库回退模式，基础知识点信息仍可正常浏览。\n配置个人 AI API 密钥后可解锁完整智能解说功能。` }] }));
    }
  };

  const handleLanguageChange = useCallback((newLang: SupportedLanguage) => {
    setLanguage(newLang);
    const opt = LANGUAGE_OPTIONS.find((o) => o.value === newLang);
    if (opt) setCode(opt.defaultCode);
    setExecResult(null); setRunError(""); setLastBackend(null); setPreviewHtml(null);
    setAnnotatedCode(null); setShowAnnotated(false); setSelectedChapter(null);
    setStructuredError(null); setSecurityViolations([]); setPeakMemoryMb(null);
    setOutputTab("output");
    loadCoursesForLanguage(newLang);
  }, []);

  const handleRun = useCallback(async () => {
    setIsRunning(true); setRunError(""); setStructuredError(null); setSecurityViolations([]);
    try {
      const response: ExecutionResponse = await executionDispatcher.execute({ code, language, kpId: currentKpId || undefined });
      if (response.previewHtml || (response.success && isFrontendLanguage(language))) {
        const html = response.previewHtml || response.stdout;
        setPreviewHtml(html);
        setExecResult({ success: true, stdout: "预览已生成", stderr: "", exit_code: 0, execution_time_ms: response.executionTimeMs, memory_used_mb: response.memoryUsedMb, error_type: null, error_message: null });
      } else {
        setExecResult({
          success: response.success, stdout: response.stdout, stderr: response.stderr,
          exit_code: response.exitCode, execution_time_ms: response.executionTimeMs,
          memory_used_mb: response.memoryUsedMb, error_type: response.errorType, error_message: response.errorMessage,
        });
        setPreviewHtml(null);
      }
      setLastBackend({ backend: response.backend, reason: "" });
      setBackendStatuses(executionDispatcher.getBackendStatuses());

      const entry: ExecHistoryEntry = {
        id: Date.now().toString(36) + Math.random().toString(36).slice(2, 6),
        timestamp: Date.now(), language, code,
        success: response.success, exitCode: response.exitCode,
        executionTimeMs: response.executionTimeMs, peakMemoryMb: response.memoryUsedMb || null,
        error: null, stdout: response.stdout, stderr: response.stderr,
      };
      const newHistory = [...execHistory, entry].slice(-50);
      setExecHistory(newHistory);
      saveHistory(newHistory);

      if (!response.success) setOutputTab("problems");
      if (response.success && currentKpId) requestCodeAnnotation(code, language, currentKpId);
    } catch {
      const msg = "执行失败，请检查代码或稍后重试";
      setRunError(msg);
      setExecResult({ success: false, stdout: "", stderr: msg, exit_code: -1, execution_time_ms: 0, memory_used_mb: 0, error_type: "unknown", error_message: msg });
      setOutputTab("problems");
    } finally { setIsRunning(false); }
  }, [code, language, currentKpId, execHistory]);

  const requestCodeAnnotation = async (codeToAnnotate: string, lang: string, kpId?: string) => {
    setIsAnnotating(true);
    try {
      const { data } = await learningApi.annotateCode({ code: codeToAnnotate, language: lang, kp_id: kpId });
      setAnnotatedCode(data.annotated_code);
      const annotationMsg = [`📝 **代码注解**`, "", data.explanation, data.key_concepts.length > 0 ? `\n🔑 涉及概念：${data.key_concepts.join("、")}` : ""].filter(Boolean).join("\n");
      useChatStore.setState((state) => ({ messages: [...state.messages, { role: "assistant", content: annotationMsg }] }));
      chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
    } catch { setAnnotatedCode(null); }
    finally { setIsAnnotating(false); }
  };

  const handleSubmit = async () => {
    if (!currentKpId) { setRunError("请先从左侧章节中选择一个知识点再提交"); return; }
    setIsRunning(true); setRunError("");
    try { await learningApi.submitCode({ code, kp_id: currentKpId, language }); await loadLearningPath(); await loadKnowledgeStates(); }
    catch { setRunError("提交失败，请重试"); }
    finally { setIsRunning(false); }
  };

  const handleChatSend = async () => {
    if (!chatInput.trim() || !currentKpId) return;
    const msg = chatInput; setChatInput("");
    await sendMessage(currentKpId, msg);
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const handleRequestHint = async () => {
    if (!currentKpId) return;
    await sendMessage(currentKpId, "我需要一点提示");
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const jumpToLine = (line: number) => {
    if (editorRef.current) {
      editorRef.current.revealLineInCenter(line);
      editorRef.current.setPosition({ lineNumber: line, column: 1 });
      editorRef.current.focus();
    }
  };

  const restoreFromHistory = (entry: ExecHistoryEntry) => {
    setLanguage(entry.language as SupportedLanguage);
    setCode(entry.code);
    setExecResult({ success: entry.success, stdout: entry.stdout, stderr: entry.stderr, exit_code: entry.exitCode, execution_time_ms: entry.executionTimeMs, memory_used_mb: entry.peakMemoryMb || 0, error_type: null, error_message: null });
    setOutputTab("output");
  };

  const currentLangOption = LANGUAGE_OPTIONS.find((o) => o.value === language);
  const wasmStatus = backendStatuses.find((b) => b.type === "wasm");
  const isWasmLoading = wasmStatus && !wasmStatus.available && wasmProgress < 100;
  const showPreview = isFrontendLanguage(language) && previewHtml;
  const errorCount = (execResult && !execResult.success) ? 1 : 0;
  const hasInputCall = language === "python" && /\binput\s*\(/.test(code);

  return (
    <div className="code-workspace">
      {coursePanelOpen && (
        <div className="course-sidebar-panel">
          <div className="course-sidebar-header">
            <Library size={16} /><span>课程章节</span>
            <button className="course-panel-toggle" onClick={() => setCoursePanelOpen(false)} title="收起面板"><ChevronRight size={14} /></button>
          </div>
          <div className="course-book-tabs">
            {courses.map((c) => (
              <button key={c.id} className={`course-book-tab ${selectedCourse === c.id ? "active" : ""}`} onClick={() => selectCourse(c.id)} title={c.subtitle || c.title}>
                <span className="book-tab-title">{c.title.length > 18 ? c.title.slice(0, 18) + "…" : c.title}</span>
                <span className="book-tab-meta">{c.author} · {c.total_chapters}章</span>
              </button>
            ))}
            {coursesLoading && <div className="course-loading-hint"><Loader2 size={12} className="spinning" /> 加载中…</div>}
            {!coursesLoading && courses.length === 0 && <div className="course-empty-hint">该语言暂无参考书籍课程</div>}
          </div>
          <div className="course-chapter-tree">
            {Object.entries(groupedChapters).map(([partNum, part]) => (
              <div key={partNum} className="chapter-part-group">
                <button className="part-toggle" onClick={() => togglePart(Number(partNum))}>
                  {expandedParts.has(Number(partNum)) ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                  <span className="part-badge">P{partNum}</span><span className="part-label">{part.part_title}</span>
                </button>
                {expandedParts.has(Number(partNum)) && part.items.map((ch) => (
                  <button key={ch.id} className={`chapter-tree-item ${selectedChapter?.chapter.id === ch.id ? "active" : ""}`} onClick={() => selectChapter(ch)}>
                    <span className="ch-num">{ch.chapter_number}</span><span className="ch-title">{ch.chapter_title}</span><span className="ch-diff">{difficultyStars(ch.difficulty)}</span>
                  </button>
                ))}
              </div>
            ))}
          </div>
          {selectedChapter && (
            <div className="chapter-quick-info">
              <div className="chqi-title">第{selectedChapter.chapter.chapter_number}章 · {selectedChapter.chapter.chapter_title}</div>
              {selectedChapter.chapter.learning_objectives && (
                <div className="chqi-objectives">
                  {selectedChapter.chapter.learning_objectives.slice(0, 3).map((obj, i) => (<div key={i} className="chqi-obj">✓ {obj}</div>))}
                  {selectedChapter.chapter.learning_objectives.length > 3 && <div className="chqi-more">…还有{selectedChapter.chapter.learning_objectives.length - 3}个目标</div>}
                </div>
              )}
              {selectedChapter.chapter.key_concepts && (
                <div className="chqi-concepts">{selectedChapter.chapter.key_concepts.slice(0, 5).map((c, i) => (<span key={i} className="chqi-tag">{c}</span>))}</div>
              )}
              {selectedChapter.knowledge_points.length > 0 && (
                <div className="chqi-kps">
                  {selectedChapter.knowledge_points.map((kp) => (
                    <button key={kp.id} className={`chqi-kp-btn ${currentKpId === kp.id ? "active" : ""} mastery-${kp.mastery_level}`} onClick={() => setCurrentKpId(kp.id)}>
                      {kp.title}<span className="chqi-kp-pct">{Math.round(kp.bkt_p_know * 100)}%</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
      {!coursePanelOpen && (
        <button className="course-panel-open-btn" onClick={() => setCoursePanelOpen(true)} title="展开课程面板"><Library size={16} /></button>
      )}

      <div className="workspace-main">
        <div className="editor-panel">
          <div className="editor-toolbar">
            <select value={language} onChange={(e) => handleLanguageChange(e.target.value as SupportedLanguage)} className="language-select">
              {LANGUAGE_OPTIONS.map((opt) => (<option key={opt.value} value={opt.value}>{opt.label}</option>))}
            </select>
            <div className="backend-indicators">
              {backendStatuses.map((b) => (
                <span key={b.type} className={`backend-dot ${b.available ? "available" : "unavailable"} ${lastBackend?.backend === b.type ? "active" : ""}`}
                  title={`${b.label}: ${b.available ? "可用" : "不可用"}${b.latency ? ` (${b.latency}ms)` : ""}`}>
                  {BACKEND_ICONS[b.type]}
                </span>
              ))}
              {isWasmLoading && <span className="wasm-progress-inline"><Loader2 size={10} className="spinning" /> {wasmProgress}%</span>}
            </div>
            <div className="toolbar-actions">
              <button onClick={handleRun} disabled={isRunning} className="btn-run" title="运行代码 (Ctrl+Enter)">
                <Play size={16} /> {isRunning ? "运行中..." : "运行"}
              </button>
              {isRunning && <button className="btn-stop" title="停止执行"><StopCircle size={16} /></button>}
              <button onClick={handleSubmit} disabled={isRunning || !currentKpId} className="btn-submit" title={currentKpId ? "提交代码" : "请先选择知识点"}>
                <Send size={16} /> 提交
              </button>
              <button onClick={() => { setCode(currentLangOption?.defaultCode || ""); setExecResult(null); setRunError(""); setLastBackend(null); setPreviewHtml(null); setAnnotatedCode(null); setShowAnnotated(false); setStructuredError(null); setSecurityViolations([]); }} className="btn-reset" title="重置">
                <RotateCcw size={16} />
              </button>
              {annotatedCode && (
                <button onClick={() => setShowAnnotated(!showAnnotated)} className={`btn-annotate ${showAnnotated ? "active" : ""}`} title={showAnnotated ? "查看原始代码" : "查看注解代码"}>
                  <BookOpen size={16} />
                </button>
              )}
              {isAnnotating && <Loader2 size={16} className="spinning" />}
              <span className="shortcut-hint" title="快捷键"><Keyboard size={12} /> Ctrl+Enter</span>
            </div>
          </div>

          {!currentKpId && (
            <div className="editor-notice"><AlertCircle size={14} /><span>自由练习模式 — 从左侧选择课程章节开始系统学习</span></div>
          )}

          <Editor height="350px" language={currentLangOption?.monacoLang || "plaintext"} value={showAnnotated && annotatedCode ? annotatedCode : code}
            onChange={(val) => { if (!showAnnotated) setCode(val || ""); }} theme="vs-dark"
            onMount={(editor) => { editorRef.current = editor; }}
            options={{ fontSize: 14, minimap: { enabled: false }, wordWrap: "on", automaticLayout: true, readOnly: showAnnotated, scrollBeyondLastLine: false, renderLineHighlight: "all" }} />
        </div>

        {hasInputCall && (
          <div className={`stdin-section ${showStdin ? "expanded" : "collapsed"}`}>
            <button className="stdin-toggle" onClick={() => setShowStdin(!showStdin)}>
              {showStdin ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              <span>标准输入 (stdin)</span>
              <span className="stdin-hint">检测到 input() 调用，请在此输入数据</span>
            </button>
            {showStdin && (
              <textarea className="stdin-textarea" value={stdinInput} onChange={(e) => setStdinInput(e.target.value)}
                placeholder="每行一个输入值，按 Enter 分隔&#10;例如：&#10;Alice&#10;25" rows={3} />
            )}
          </div>
        )}

        <div className="output-panel">
          <div className="output-tabs">
            <button className={`output-tab ${outputTab === "output" ? "active" : ""}`} onClick={() => setOutputTab("output")}>
              <Terminal size={12} /> 输出
            </button>
            <button className={`output-tab ${outputTab === "problems" ? "active" : ""}`} onClick={() => setOutputTab("problems")}>
              <AlertTriangle size={12} /> 问题
              {errorCount > 0 && <span className="output-tab-badge error">{errorCount}</span>}
            </button>
            <button className={`output-tab ${outputTab === "terminal" ? "active" : ""}`} onClick={() => setOutputTab("terminal")}>
              <Terminal size={12} /> 终端
            </button>
            <button className={`output-tab ${outputTab === "history" ? "active" : ""}`} onClick={() => setOutputTab("history")}>
              <History size={12} /> 历史
              {execHistory.length > 0 && <span className="output-tab-badge">{execHistory.length}</span>}
            </button>
            <div className="output-tabs-spacer" />
            {lastBackend && <span className="output-backend-tag" title={lastBackend.reason}>{BACKEND_ICONS[lastBackend.backend]}{BACKEND_LABELS[lastBackend.backend]}</span>}
          </div>

          {outputTab === "output" && (
            <div className="output-tab-content">
              {runError && <div className="output-error-banner"><AlertCircle size={14} /> {runError}</div>}
              {securityViolations.length > 0 && (
                <div className="security-violations-banner">
                  <AlertTriangle size={14} /> 安全检查未通过：
                  {securityViolations.map((v, i) => <div key={i} className="violation-item">{v}</div>)}
                </div>
              )}
              {showPreview ? (
                <div className="preview-container"><iframe ref={previewRef} srcDoc={previewHtml} className="preview-iframe" title="Preview" sandbox="allow-scripts" /></div>
              ) : execResult ? (
                <div className={`output-content ${execResult.success ? "success" : "error"}`}>
                  {execResult.stdout && <pre className="stdout">{execResult.stdout}</pre>}
                  {execResult.stderr && <pre className="stderr">{execResult.stderr}</pre>}
                </div>
              ) : (
                <div className="output-placeholder">点击"运行"查看{isFrontendLanguage(language) ? "预览" : "输出"} <span className="shortcut-hint-inline">Ctrl+Enter</span></div>
              )}
            </div>
          )}

          {outputTab === "problems" && (
            <div className="output-tab-content">
              {structuredError ? (
                <div className="problem-item error">
                  <div className="problem-header">
                    <XCircle size={14} className="problem-icon error" />
                    <span className="problem-type">{structuredError.error_type}</span>
                    {structuredError.line_number && (
                      <button className="problem-line-link" onClick={() => jumpToLine(structuredError.line_number!)}>
                        行 {structuredError.line_number}{structuredError.column ? `:${structuredError.column}` : ""}
                      </button>
                    )}
                  </div>
                  <div className="problem-message">{structuredError.message}</div>
                  {structuredError.suggestion && (
                    <div className="problem-suggestion">
                      <Lightbulb size={12} /> {structuredError.suggestion}
                    </div>
                  )}
                </div>
              ) : execResult && !execResult.success ? (
                <div className="problem-item error">
                  <div className="problem-header">
                    <XCircle size={14} className="problem-icon error" />
                    <span className="problem-type">{execResult.error_type || "执行错误"}</span>
                  </div>
                  <div className="problem-message">{execResult.error_message || execResult.stderr || "未知错误"}</div>
                </div>
              ) : securityViolations.length > 0 ? (
                securityViolations.map((v, i) => (
                  <div key={i} className="problem-item warning">
                    <div className="problem-header">
                      <AlertTriangle size={14} className="problem-icon warning" />
                      <span className="problem-type">安全违规</span>
                    </div>
                    <div className="problem-message">{v}</div>
                  </div>
                ))
              ) : (
                <div className="output-placeholder">没有发现问题 ✅</div>
              )}
            </div>
          )}

          {outputTab === "terminal" && execResult && (
            <div className="output-tab-content terminal-view">
              <div className="terminal-line cmd">$ {language === "python" ? "python3" : language === "javascript" ? "node" : language === "rust" ? "rustc && ./main" : language} main.{language === "python" ? "py" : language === "javascript" ? "js" : language === "rust" ? "rs" : "jsx"}</div>
              {execResult.stdout && execResult.stdout.split("\n").map((line, i) => <div key={i} className="terminal-line stdout">{line}</div>)}
              {execResult.stderr && execResult.stderr.split("\n").map((line, i) => <div key={i} className="terminal-line stderr">{line}</div>)}
              <div className="terminal-line exit">
                进程退出，退出码: {execResult.exit_code}
              </div>
              <div className="exec-stats-bar">
                <span className="exec-stat"><Clock size={11} /> {execResult.execution_time_ms}ms</span>
                <span className="exec-stat"><HardDrive size={11} /> {(execResult.memory_used_mb || 0).toFixed(1)}MB</span>
                <span className="exec-stat"><Zap size={11} /> 退出码: {execResult.exit_code}</span>
                {lastBackend && <span className="exec-stat">{BACKEND_ICONS[lastBackend.backend]} {BACKEND_LABELS[lastBackend.backend]}</span>}
              </div>
            </div>
          )}

          {outputTab === "terminal" && !execResult && (
            <div className="output-tab-content terminal-view">
              <div className="terminal-line cmd">$ _</div>
              <div className="output-placeholder">运行代码后查看终端输出</div>
            </div>
          )}

          {outputTab === "history" && (
            <div className="output-tab-content history-view">
              {execHistory.length === 0 ? (
                <div className="output-placeholder">暂无执行历史</div>
              ) : (
                [...execHistory].reverse().map((entry) => (
                  <div key={entry.id} className={`history-item ${entry.success ? "success" : "error"}`} onClick={() => restoreFromHistory(entry)}>
                    <div className="history-item-header">
                      <span className={`history-status ${entry.success ? "success" : "error"}`}>{entry.success ? "✓" : "✗"}</span>
                      <span className="history-lang">{entry.language}</span>
                      <span className="history-time">{new Date(entry.timestamp).toLocaleTimeString()}</span>
                      <span className="history-duration">{entry.executionTimeMs}ms</span>
                    </div>
                    <div className="history-code-preview">{entry.code.split("\n")[0].slice(0, 60)}</div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      </div>

      <div className="workspace-sidebar">
        <div className="tutor-status">
          <div className="status-item"><span className="status-label">教学角色</span><span className="status-value persona">{PERSONA_LABELS[personaStage] || personaStage}</span></div>
          <div className="status-item"><span className="status-label">推理阶段</span><span className="status-value ercf">{ERCF_LABELS[ercfStage] || ercfStage}</span></div>
          {hintLevel !== null && (<div className="status-item"><span className="status-label">提示等级</span><span className="status-value hint">L{hintLevel}</span></div>)}
        </div>
        <div className="execution-backends">
          <h4>执行引擎</h4>
          {backendStatuses.map((b) => (
            <div key={b.type} className={`backend-item ${b.available ? "available" : "unavailable"}`}>
              <span className="backend-status-dot" /><span className="backend-name">{b.label}</span>
              {b.available && b.latency > 0 && (<span className="backend-latency">{b.latency}ms</span>)}
              {b.type === "wasm" && !b.available && wasmProgress > 0 && wasmProgress < 100 && (
                <span className="wasm-progress"><Loader2 size={12} className="spinning" /> {wasmProgress}%</span>
              )}
            </div>
          ))}
        </div>
        <div className="chat-panel">
          <div className="chat-messages">
            {messages.length === 0 && !currentKpId && (<div className="chat-placeholder">从左侧选择课程章节，开始系统学习</div>)}
            {messages.length === 0 && currentKpId && (<div className="chat-placeholder"><Loader2 size={14} className="spinning" /> 正在加载知识点解说...</div>)}
            {messages.map((msg, i) => (
              <div key={i} className={`chat-msg ${msg.role}`}>
                <span className="msg-role">{msg.role === "user" ? "你" : <><MessageSquare size={12} /> 导师</>}</span>
                <p className="chat-msg-content" dangerouslySetInnerHTML={{
                  __html: msg.content
                    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
                    .replace(/```(\w*)\n([\s\S]*?)```/g, "<pre><code>$2</code></pre>")
                    .replace(/`([^`]+)`/g, "<code>$1</code>")
                    .replace(/\n/g, "<br/>")
                }} />
              </div>
            ))}
            {isLoading && <div className="chat-msg assistant typing">导师正在思考...</div>}
            <div ref={chatEndRef} />
          </div>
          <div className="chat-input-area">
            <button onClick={handleRequestHint} className="btn-hint" title="请求提示" disabled={!currentKpId}><Lightbulb size={16} /></button>
            <input type="text" value={chatInput} onChange={(e) => setChatInput(e.target.value)} onKeyDown={(e) => e.key === "Enter" && handleChatSend()}
              placeholder={currentKpId ? "向AI导师提问..." : "请先选择知识点"} className="chat-input" disabled={!currentKpId} />
            <button onClick={handleChatSend} disabled={isLoading || !currentKpId} className="btn-send"><Send size={16} /></button>
          </div>
        </div>
      </div>
    </div>
  );
}
