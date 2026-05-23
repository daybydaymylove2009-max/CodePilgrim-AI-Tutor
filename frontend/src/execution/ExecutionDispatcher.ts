import { learningApi } from "../api";
import type { ExecutionRequest, ExecutionResponse, BackendStatus, DispatchDecision } from "./types";
import { dispatch } from "./types";
import { wasmEngine } from "./WasmEngine";
import { agentConnector } from "./AgentConnector";

type ExecutionListener = (response: ExecutionResponse, decision: DispatchDecision) => void;

class ExecutionDispatcher {
  private listeners: Set<ExecutionListener> = new Set();
  private serverLatency: number = 0;
  private wasmLatency: number = 0;
  private agentLatency: number = 0;

  onResult(listener: ExecutionListener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  getBackendStatuses(): BackendStatus[] {
    return [
      {
        type: "wasm",
        available: wasmEngine.isReady,
        latency: this.wasmLatency,
        label: wasmEngine.isReady ? "浏览器 WASM" : "WASM 加载中...",
      },
      {
        type: "agent",
        available: agentConnector.isAvailable,
        latency: this.agentLatency,
        label: agentConnector.isAvailable ? "本地 Agent" : "Agent 未连接",
      },
      {
        type: "server",
        available: true,
        latency: this.serverLatency,
        label: "服务端",
      },
    ];
  }

  async execute(request: ExecutionRequest): Promise<ExecutionResponse> {
    const backends = this.getBackendStatuses();
    const decision = dispatch(request.code, request.language, backends);

    let response: ExecutionResponse;

    switch (decision.backend) {
      case "wasm":
        response = await this.executeWasm(request);
        if (!response.success && response.errorType === "wasm_error") {
          response = await this.executeServer(request);
        }
        break;
      case "agent":
        response = await this.executeAgent(request);
        if (!response.success && response.errorType === "agent_unavailable") {
          response = await this.executeServer(request);
        }
        break;
      case "server":
      default:
        response = await this.executeServer(request);
        break;
    }

    for (const listener of this.listeners) {
      listener(response, decision);
    }

    return response;
  }

  private async executeWasm(request: ExecutionRequest): Promise<ExecutionResponse> {
    const start = performance.now();
    try {
      if (!wasmEngine.isReady) {
        const initialized = await wasmEngine.init();
        if (!initialized) {
          return {
            success: false,
            stdout: "",
            stderr: "WASM 引擎不可用",
            exitCode: -1,
            executionTimeMs: 0,
            memoryUsedMb: 0,
            errorType: "wasm_error",
            errorMessage: "WASM 引擎初始化失败",
            backend: "wasm",
          };
        }
      }
      const result = await wasmEngine.execute(request);
      this.wasmLatency = Math.round(performance.now() - start);
      return result;
    } catch (e) {
      this.wasmLatency = Math.round(performance.now() - start);
      return {
        success: false,
        stdout: "",
        stderr: e instanceof Error ? e.message : String(e),
        exitCode: -1,
        executionTimeMs: 0,
        memoryUsedMb: 0,
        errorType: "wasm_error",
        errorMessage: e instanceof Error ? e.message : String(e),
        backend: "wasm",
      };
    }
  }

  private async executeAgent(request: ExecutionRequest): Promise<ExecutionResponse> {
    const start = performance.now();
    try {
      const result = await agentConnector.execute(request);
      this.agentLatency = Math.round(performance.now() - start);
      return result;
    } catch (e) {
      this.agentLatency = Math.round(performance.now() - start);
      return {
        success: false,
        stdout: "",
        stderr: e instanceof Error ? e.message : String(e),
        exitCode: -1,
        executionTimeMs: 0,
        memoryUsedMb: 0,
        errorType: "agent_error",
        errorMessage: e instanceof Error ? e.message : String(e),
        backend: "agent",
      };
    }
  }

  private async executeServer(request: ExecutionRequest): Promise<ExecutionResponse> {
    const start = performance.now();
    try {
      const { data } = await learningApi.executeCode({
        code: request.code,
        kp_id: request.kpId,
        language: request.language,
      });
      this.serverLatency = Math.round(performance.now() - start);
      return {
        success: data.success,
        stdout: data.stdout || "",
        stderr: data.stderr || "",
        exitCode: data.exit_code,
        executionTimeMs: data.execution_time_ms,
        memoryUsedMb: data.memory_used_mb,
        errorType: data.error_type,
        errorMessage: data.error_message,
        backend: "server",
      };
    } catch (e) {
      this.serverLatency = Math.round(performance.now() - start);
      const resp = (e as { response?: { data?: { detail?: string } } })?.response?.data;
      const msg = resp?.detail || "服务端执行失败";
      return {
        success: false,
        stdout: "",
        stderr: msg,
        exitCode: -1,
        executionTimeMs: 0,
        memoryUsedMb: 0,
        errorType: "server_error",
        errorMessage: msg,
        backend: "server",
      };
    }
  }

  async initWasm(onProgress?: (progress: number) => void): Promise<boolean> {
    return wasmEngine.init(onProgress);
  }

  async checkAgent(): Promise<boolean> {
    return agentConnector.checkAvailability();
  }

  async measureServerLatency(): Promise<number> {
    const start = performance.now();
    try {
      await fetch("http://localhost:8000/health", { method: "GET" }).catch(() => {});
    } catch {}
    this.serverLatency = Math.round(performance.now() - start);
    return this.serverLatency;
  }
}

export const executionDispatcher = new ExecutionDispatcher();
