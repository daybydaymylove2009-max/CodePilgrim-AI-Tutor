export type ExecutionBackendType = "wasm" | "agent" | "server";

export type SupportedLanguage = "python" | "javascript" | "rust" | "react" | "vue";

export interface ExecutionRequest {
  code: string;
  language: SupportedLanguage;
  kpId?: string;
  timeout?: number;
}

export interface ExecutionResponse {
  success: boolean;
  stdout: string;
  stderr: string;
  exitCode: number;
  executionTimeMs: number;
  memoryUsedMb: number;
  errorType: string | null;
  errorMessage: string | null;
  backend: ExecutionBackendType;
  previewHtml?: string;
}

export interface BackendStatus {
  type: ExecutionBackendType;
  available: boolean;
  latency: number;
  label: string;
}

export interface DispatchDecision {
  backend: ExecutionBackendType;
  reason: string;
}

export interface AgentMessage {
  type: "execute" | "ping" | "pong" | "result" | "error" | "status";
  id: string;
  payload?: Record<string, unknown>;
}

const UNSUPPORTED_PYODIDE_PATTERNS = [
  /\bimport\s+os\b/,
  /\bimport\s+subprocess\b/,
  /\bimport\s+socket\b/,
  /\bimport\s+http\b/,
  /\bfrom\s+os\b/,
  /\bfrom\s+subprocess\b/,
  /\bfrom\s+socket\b/,
  /\bfrom\s+http\b/,
  /\bopen\s*\(/,
];

export function shouldUseWasm(code: string, language: SupportedLanguage): boolean {
  if (language === "python") {
    for (const pattern of UNSUPPORTED_PYODIDE_PATTERNS) {
      if (pattern.test(code)) return false;
    }
    return true;
  }
  if (language === "react" || language === "vue") return true;
  if (language === "javascript") return true;
  return false;
}

export function requiresFullEnvironment(code: string, language: SupportedLanguage): boolean {
  if (language === "rust") return true;
  if (language === "react" || language === "vue") return false;

  const fullEnvPatterns = [
    /\bimport\s+(flask|django|fastapi|requests|urllib|sqlalchemy)\b/,
    /\bfrom\s+(flask|django|fastapi|requests|urllib|sqlalchemy)\b/,
    /\bopen\s*\(\s*['"][^']*['"]\s*,\s*['"]w/,
    /\bsocket\b/,
    /\bsubprocess\b/,
    /\bthreading\b/,
    /\bmultiprocessing\b/,
  ];

  return fullEnvPatterns.some((p) => p.test(code));
}

export function isFrontendLanguage(language: SupportedLanguage): boolean {
  return language === "react" || language === "vue";
}

export function dispatch(
  code: string,
  language: SupportedLanguage,
  backends: BackendStatus[]
): DispatchDecision {
  const available = backends.filter((b) => b.available);

  if (available.length === 0) {
    return { backend: "server", reason: "无可用后端，使用服务端兜底" };
  }

  if (language === "react" || language === "vue") {
    const wasm = available.find((b) => b.type === "wasm");
    if (wasm) return { backend: "wasm", reason: `${language} 在浏览器编译渲染，零延迟实时预览` };
    const server = available.find((b) => b.type === "server");
    if (server) return { backend: "server", reason: "使用服务端编译前端代码" };
  }

  if (language === "javascript") {
    const wasm = available.find((b) => b.type === "wasm");
    if (wasm) return { backend: "wasm", reason: "JavaScript 在浏览器执行，零延迟" };
    const server = available.find((b) => b.type === "server");
    if (server) return { backend: "server", reason: "浏览器不支持JS，使用服务端" };
  }

  if (language === "rust") {
    const agent = available.find((b) => b.type === "agent");
    if (agent) return { backend: "agent", reason: "Rust 需要本地编译环境，使用本地Agent" };
    const server = available.find((b) => b.type === "server");
    if (server) return { backend: "server", reason: "Rust 需要编译环境，使用服务端执行" };
  }

  if (requiresFullEnvironment(code, language)) {
    const agent = available.find((b) => b.type === "agent");
    if (agent) return { backend: "agent", reason: "代码需要完整运行环境，使用本地Agent" };
    const server = available.find((b) => b.type === "server");
    if (server) return { backend: "server", reason: "代码需要完整环境，使用服务端Docker" };
  }

  if (shouldUseWasm(code, language)) {
    const wasm = available.find((b) => b.type === "wasm");
    if (wasm) return { backend: "wasm", reason: "简单Python代码，浏览器WASM执行，零服务端开销" };
  }

  const agent = available.find((b) => b.type === "agent");
  if (agent) return { backend: "agent", reason: "本地Agent可用，就近执行" };

  const server = available.find((b) => b.type === "server");
  if (server) return { backend: "server", reason: "使用服务端执行" };

  return { backend: "server", reason: "默认服务端执行" };
}
