import type { ExecutionRequest, ExecutionResponse, AgentMessage } from "./types";

const AGENT_WS_URL = "ws://localhost:18765";
const AGENT_HTTP_URL = "http://localhost:18765";
const PING_INTERVAL = 15000;
const RECONNECT_DELAY = 5000;
const MAX_RECONNECT_ATTEMPTS = 3;

class AgentConnector {
  private ws: WebSocket | null = null;
  private connected: boolean = false;
  private connecting: boolean = false;
  private reconnectAttempts: number = 0;
  private pendingRequests: Map<
    string,
    {
      resolve: (result: ExecutionResponse) => void;
      reject: (error: Error) => void;
      timer: ReturnType<typeof setTimeout>;
    }
  > = new Map();
  private pingTimer: ReturnType<typeof setInterval> | null = null;
  private messageId: number = 0;

  get isAvailable(): boolean {
    return this.connected;
  }

  get isConnecting(): boolean {
    return this.connecting;
  }

  async connect(): Promise<boolean> {
    if (this.connected) return true;
    if (this.connecting) return false;

    this.connecting = true;

    return new Promise<boolean>((resolve) => {
      try {
        const ws = new WebSocket(AGENT_WS_URL);

        const timeout = setTimeout(() => {
          if (!this.connected) {
            ws.close();
            this.connecting = false;
            resolve(false);
          }
        }, 3000);

        ws.onopen = () => {
          clearTimeout(timeout);
          this.connected = true;
          this.connecting = false;
          this.reconnectAttempts = 0;
          this.ws = ws;
          this.startPing();
          resolve(true);
        };

        ws.onclose = () => {
          clearTimeout(timeout);
          this.connected = false;
          this.connecting = false;
          this.ws = null;
          this.stopPing();
          this.rejectAllPending("连接断开");
          this.attemptReconnect();
          resolve(false);
        };

        ws.onerror = () => {
          clearTimeout(timeout);
          this.connected = false;
          this.connecting = false;
          resolve(false);
        };

        ws.onmessage = (event) => {
          this.handleMessage(event.data);
        };
      } catch {
        this.connecting = false;
        resolve(false);
      }
    });
  }

  async checkAvailability(): Promise<boolean> {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 2000);

      const response = await fetch(`${AGENT_HTTP_URL}/health`, {
        signal: controller.signal,
      });
      clearTimeout(timeoutId);

      if (response.ok) {
        if (!this.connected) {
          await this.connect();
        }
        return true;
      }
      return false;
    } catch {
      return false;
    }
  }

  async execute(request: ExecutionRequest): Promise<ExecutionResponse> {
    if (!this.connected) {
      const connected = await this.connect();
      if (!connected) {
        return {
          success: false,
          stdout: "",
          stderr: "本地 Agent 不可用，请确保 CodePilgrim Agent 已启动",
          exitCode: -1,
          executionTimeMs: 0,
          memoryUsedMb: 0,
          errorType: "agent_unavailable",
          errorMessage: "本地 Agent 不可用",
          backend: "agent",
        };
      }
    }

    const id = this.nextId();
    const message: AgentMessage = {
      type: "execute",
      id,
      payload: {
        code: request.code,
        language: request.language,
        timeout: request.timeout || 10,
      },
    };

    return new Promise<ExecutionResponse>((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pendingRequests.delete(id);
        reject(new Error("执行超时"));
      }, (request.timeout || 10) * 1000 + 2000);

      this.pendingRequests.set(id, { resolve, reject, timer });
      this.ws!.send(JSON.stringify(message));
    });
  }

  private handleMessage(data: string): void {
    try {
      const message: AgentMessage = JSON.parse(data);

      if (message.type === "pong") return;

      if (message.type === "result" || message.type === "error") {
        const pending = this.pendingRequests.get(message.id);
        if (!pending) return;

        clearTimeout(pending.timer);
        this.pendingRequests.delete(message.id);

        if (message.type === "result") {
          const payload = message.payload || {};
          pending.resolve({
            success: payload.success as boolean ?? false,
            stdout: (payload.stdout as string) || "",
            stderr: (payload.stderr as string) || "",
            exitCode: (payload.exit_code as number) ?? -1,
            executionTimeMs: (payload.execution_time_ms as number) || 0,
            memoryUsedMb: (payload.memory_used_mb as number) || 0,
            errorType: (payload.error_type as string) || null,
            errorMessage: (payload.error_message as string) || null,
            backend: "agent",
          });
        } else {
          pending.resolve({
            success: false,
            stdout: "",
            stderr: (message.payload?.error as string) || "Agent 执行失败",
            exitCode: -1,
            executionTimeMs: 0,
            memoryUsedMb: 0,
            errorType: "agent_error",
            errorMessage: (message.payload?.error as string) || "Agent 执行失败",
            backend: "agent",
          });
        }
      }
    } catch {}
  }

  private startPing(): void {
    this.stopPing();
    this.pingTimer = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: "ping", id: this.nextId() }));
      }
    }, PING_INTERVAL);
  }

  private stopPing(): void {
    if (this.pingTimer) {
      clearInterval(this.pingTimer);
      this.pingTimer = null;
    }
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) return;
    this.reconnectAttempts++;
    setTimeout(() => {
      this.connect();
    }, RECONNECT_DELAY);
  }

  private rejectAllPending(reason: string): void {
    for (const [id, pending] of this.pendingRequests) {
      clearTimeout(pending.timer);
      pending.reject(new Error(reason));
    }
    this.pendingRequests.clear();
  }

  private nextId(): string {
    return `msg_${++this.messageId}_${Date.now()}`;
  }

  disconnect(): void {
    this.stopPing();
    this.rejectAllPending("主动断开");
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.connected = false;
  }
}

export const agentConnector = new AgentConnector();
