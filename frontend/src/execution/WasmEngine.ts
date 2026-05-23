import type { PyodideInterface } from "pyodide";
import { loadPyodide } from "pyodide";

const VENDOR_BASE = `${window.location.protocol}//${window.location.host}/static/vendor`;
const PYODIDE_BASE = `${window.location.protocol}//${window.location.host}/static/vendor/pyodide`;

const REACT_TEMPLATE = `<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>body{margin:0;font-family:sans-serif;}</style>
<script src="${VENDOR_BASE}/react.development.js"><\/script>
<script src="${VENDOR_BASE}/react-dom.development.js"><\/script>
<script src="${VENDOR_BASE}/babel.min.js"><\/script>
</head><body><div id="root"></div>
<script type="text/babel">
{{CODE}}
</script></body></html>`;

const VUE_TEMPLATE = `<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>body{margin:0;font-family:sans-serif;}</style>
<script src="${VENDOR_BASE}/vue.global.js"><\/script>
</head><body><div id="app"></div>
<script>
const { createApp, ref, computed, watch, onMounted, onUnmounted } = Vue;
{{CODE}}
</script></body></html>`;

class WasmEngine {
  private pyodide: PyodideInterface | null = null;
  private loading: Promise<PyodideInterface> | null = null;
  private loadProgress: number = 0;
  private loadError: string | null = null;

  get isReady(): boolean {
    return this.pyodide !== null;
  }

  get isLoading(): boolean {
    return this.loading !== null && this.pyodide === null;
  }

  get progress(): number {
    return this.loadProgress;
  }

  get error(): string | null {
    return this.loadError;
  }

  async init(onProgress?: (progress: number) => void): Promise<boolean> {
    if (this.pyodide) return true;
    if (this.loading) {
      return this.loading.then(() => true).catch(() => false);
    }

    this.loadProgress = 0;
    this.loadError = null;

    this.loading = new Promise<PyodideInterface>(async (resolve, reject) => {
      try {
        onProgress?.(5);
        this.loadProgress = 5;

        const pyodide = await loadPyodide({ indexURL: PYODIDE_BASE });

        onProgress?.(60);
        this.loadProgress = 60;

        await pyodide.runPythonAsync(`import sys, io`);

        onProgress?.(80);
        this.loadProgress = 80;

        await pyodide.runPythonAsync(`
import json, math, random, re, collections, itertools, functools
import datetime, decimal, fractions, string, copy, statistics, typing, dataclasses
`);

        onProgress?.(100);
        this.loadProgress = 100;

        this.pyodide = pyodide;
        resolve(pyodide);
      } catch (e) {
        this.loadError = e instanceof Error ? e.message : String(e);
        this.loading = null;
        reject(e);
      }
    });

    return this.loading.then(() => true).catch(() => false);
  }

  async execute(request: ExecutionRequest): Promise<ExecutionResponse> {
    if (request.language === "react") {
      return this.executeReact(request);
    }
    if (request.language === "vue") {
      return this.executeVue(request);
    }
    if (request.language === "javascript") {
      return this.executeJavaScript(request);
    }

    return this.executePython(request);
  }

  private executeReact(request: ExecutionRequest): ExecutionResponse {
    const start = performance.now();
    try {
      const html = REACT_TEMPLATE.replace("{{CODE}}", request.code);
      return {
        success: true,
        stdout: "",
        stderr: "",
        exitCode: 0,
        executionTimeMs: Math.round(performance.now() - start),
        memoryUsedMb: 0,
        errorType: null,
        errorMessage: null,
        backend: "wasm",
        previewHtml: html,
      };
    } catch (e) {
      return {
        success: false,
        stdout: "",
        stderr: e instanceof Error ? e.message : String(e),
        exitCode: -1,
        executionTimeMs: Math.round(performance.now() - start),
        memoryUsedMb: 0,
        errorType: "compile_error",
        errorMessage: e instanceof Error ? e.message : String(e),
        backend: "wasm",
      };
    }
  }

  private executeVue(request: ExecutionRequest): ExecutionResponse {
    const start = performance.now();
    try {
      const html = VUE_TEMPLATE.replace("{{CODE}}", request.code);
      return {
        success: true,
        stdout: "",
        stderr: "",
        exitCode: 0,
        executionTimeMs: Math.round(performance.now() - start),
        memoryUsedMb: 0,
        errorType: null,
        errorMessage: null,
        backend: "wasm",
        previewHtml: html,
      };
    } catch (e) {
      return {
        success: false,
        stdout: "",
        stderr: e instanceof Error ? e.message : String(e),
        exitCode: -1,
        executionTimeMs: Math.round(performance.now() - start),
        memoryUsedMb: 0,
        errorType: "compile_error",
        errorMessage: e instanceof Error ? e.message : String(e),
        backend: "wasm",
      };
    }
  }

  private executeJavaScript(request: ExecutionRequest): ExecutionResponse {
    const start = performance.now();
    try {
      const logs: string[] = [];
      const originalLog = console.log;
      const originalError = console.error;
      console.log = (...args: unknown[]) => {
        logs.push(args.map((a) => (typeof a === "object" ? JSON.stringify(a) : String(a))).join(" "));
      };
      console.error = (...args: unknown[]) => {
        logs.push("[ERROR] " + args.map((a) => String(a)).join(" "));
      };

      const fn = new Function(request.code);
      fn();

      console.log = originalLog;
      console.error = originalError;

      return {
        success: true,
        stdout: logs.join("\n") + "\n",
        stderr: "",
        exitCode: 0,
        executionTimeMs: Math.round(performance.now() - start),
        memoryUsedMb: 0,
        errorType: null,
        errorMessage: null,
        backend: "wasm",
      };
    } catch (e) {
      return {
        success: false,
        stdout: "",
        stderr: e instanceof Error ? e.message : String(e),
        exitCode: -1,
        executionTimeMs: Math.round(performance.now() - start),
        memoryUsedMb: 0,
        errorType: "runtime_error",
        errorMessage: e instanceof Error ? e.message : String(e),
        backend: "wasm",
      };
    }
  }

  private async executePython(request: ExecutionRequest): Promise<ExecutionResponse> {
    if (!this.pyodide) {
      const initialized = await this.init();
      if (!initialized) {
        return {
          success: false, stdout: "", stderr: "WASM 引擎初始化失败",
          exitCode: -1, executionTimeMs: 0, memoryUsedMb: 0,
          errorType: "init_error", errorMessage: this.loadError || "WASM 引擎初始化失败",
          backend: "wasm",
        };
      }
    }

    const startTime = performance.now();
    try {
      this.pyodide!.runPython(`import sys, io\nsys.stdout = io.StringIO()\nsys.stderr = io.StringIO()\n`);

      const wrappedCode = `
import json
_result = {"stdout": "", "stderr": "", "exit_code": 0, "error_type": null, "error_message": null}
try:
${request.code.split("\n").map((line) => "    " + line).join("\n")}
except Exception as _e:
    _result["error_type"] = type(_e).__name__
    _result["error_message"] = str(_e)
    _result["exit_code"] = 1
finally:
    _result["stdout"] = sys.stdout.getvalue()
    _result["stderr"] = sys.stderr.getvalue()
    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__
json.dumps(_result)
`;

      const resultJson = await this.pyodide!.runPythonAsync(wrappedCode);
      const result = JSON.parse(resultJson);
      const elapsed = Math.round(performance.now() - startTime);

      return {
        success: result.exit_code === 0,
        stdout: result.stdout || "",
        stderr: result.stderr || (result.error_message ? `${result.error_type}: ${result.error_message}` : ""),
        exitCode: result.exit_code,
        executionTimeMs: elapsed,
        memoryUsedMb: 0,
        errorType: result.error_type,
        errorMessage: result.error_message,
        backend: "wasm",
      };
    } catch (e) {
      const elapsed = Math.round(performance.now() - startTime);
      return {
        success: false, stdout: "", stderr: e instanceof Error ? e.message : String(e),
        exitCode: -1, executionTimeMs: elapsed, memoryUsedMb: 0,
        errorType: "wasm_error", errorMessage: e instanceof Error ? e.message : String(e),
        backend: "wasm",
      };
    }
  }

  async loadPackage(packageName: string): Promise<boolean> {
    if (!this.pyodide) return false;
    try { await this.pyodide.loadPackage(packageName); return true; } catch { return false; }
  }

  async runPython(code: string): Promise<string> {
    if (!this.pyodide) return "";
    return await this.pyodide.runPythonAsync(code);
  }

  destroy(): void {
    if (this.pyodide) {
      try { this.pyodide.destroy(); } catch {}
      this.pyodide = null;
      this.loading = null;
      this.loadProgress = 0;
    }
  }
}

export const wasmEngine = new WasmEngine();
