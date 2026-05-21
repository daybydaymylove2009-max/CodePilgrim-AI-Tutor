import { useState, useRef } from "react";
import Editor from "@monaco-editor/react";
import { learningApi } from "../../api";
import { useLearningStore, useChatStore } from "../../store";
import type { ExecutionResult } from "../../types";
import { Play, Send, RotateCcw, Lightbulb } from "lucide-react";

const PERSONA_LABELS: Record<string, string> = {
  guide: "引路者",
  collaborator: "协作者",
  peer: "同伴",
  launcher: "发射者",
};

const ERCF_LABELS: Record<string, string> = {
  R1: "问题解析",
  R2: "概念识别",
  R3: "逻辑分解",
  R4: "错误诊断",
  R5: "引导提示",
};

export default function CodeWorkspace() {
  const [code, setCode] = useState("# 在这里编写你的代码\nprint('Hello, CodePilgrim!')\n");
  const [language, setLanguage] = useState<"python" | "javascript">("python");
  const [execResult, setExecResult] = useState<ExecutionResult | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const { currentKpId, loadLearningPath, loadKnowledgeStates } = useLearningStore();
  const { ercfStage, personaStage, hintLevel, sendMessage, messages, isLoading } = useChatStore();
  const [chatInput, setChatInput] = useState("");
  const chatEndRef = useRef<HTMLDivElement>(null);

  const handleRun = async () => {
    if (!currentKpId) return;
    setIsRunning(true);
    try {
      const { data } = await learningApi.executeCode({ code, kp_id: currentKpId, language });
      setExecResult(data);
    } catch {
      setExecResult({ success: false, stdout: "", stderr: "执行失败", exit_code: -1, execution_time_ms: 0, memory_used_mb: 0, error_type: "unknown", error_message: "执行失败" });
    } finally {
      setIsRunning(false);
    }
  };

  const handleSubmit = async () => {
    if (!currentKpId) return;
    setIsRunning(true);
    try {
      await learningApi.submitCode({ code, kp_id: currentKpId, language });
      await loadLearningPath();
      await loadKnowledgeStates();
    } catch {
      // handled silently
    } finally {
      setIsRunning(false);
    }
  };

  const handleChatSend = async () => {
    if (!chatInput.trim() || !currentKpId) return;
    const msg = chatInput;
    setChatInput("");
    await sendMessage(currentKpId, msg);
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const handleRequestHint = async () => {
    if (!currentKpId) return;
    await sendMessage(currentKpId, "我需要一点提示");
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <div className="code-workspace">
      <div className="workspace-main">
        <div className="editor-panel">
          <div className="editor-toolbar">
            <select value={language} onChange={(e) => setLanguage(e.target.value as "python" | "javascript")} className="language-select">
              <option value="python">Python</option>
              <option value="javascript">JavaScript</option>
            </select>
            <div className="toolbar-actions">
              <button onClick={handleRun} disabled={isRunning} className="btn-run" title="运行">
                <Play size={16} /> 运行
              </button>
              <button onClick={handleSubmit} disabled={isRunning} className="btn-submit" title="提交">
                <Send size={16} /> 提交
              </button>
              <button onClick={() => setCode("")} className="btn-reset" title="清空">
                <RotateCcw size={16} />
              </button>
            </div>
          </div>
          <Editor
            height="400px"
            language={language}
            value={code}
            onChange={(val) => setCode(val || "")}
            theme="vs-dark"
            options={{
              fontSize: 14,
              minimap: { enabled: false },
              wordWrap: "on",
              automaticLayout: true,
            }}
          />
        </div>

        <div className="output-panel">
          <h3>输出</h3>
          {execResult ? (
            <div className={`output-content ${execResult.success ? "success" : "error"}`}>
              {execResult.stdout && <pre className="stdout">{execResult.stdout}</pre>}
              {execResult.stderr && <pre className="stderr">{execResult.stderr}</pre>}
              <div className="output-meta">
                退出码: {execResult.exit_code} | 耗时: {execResult.execution_time_ms}ms
              </div>
            </div>
          ) : (
            <div className="output-placeholder">点击"运行"查看输出</div>
          )}
        </div>
      </div>

      <div className="workspace-sidebar">
        <div className="tutor-status">
          <div className="status-item">
            <span className="status-label">教学角色</span>
            <span className="status-value persona">{PERSONA_LABELS[personaStage] || personaStage}</span>
          </div>
          <div className="status-item">
            <span className="status-label">推理阶段</span>
            <span className="status-value ercf">{ERCF_LABELS[ercfStage] || ercfStage}</span>
          </div>
          {hintLevel !== null && (
            <div className="status-item">
              <span className="status-label">提示等级</span>
              <span className="status-value hint">L{hintLevel}</span>
            </div>
          )}
        </div>

        <div className="chat-panel">
          <div className="chat-messages">
            {messages.map((msg, i) => (
              <div key={i} className={`chat-msg ${msg.role}`}>
                <span className="msg-role">{msg.role === "user" ? "你" : "导师"}</span>
                <p>{msg.content}</p>
              </div>
            ))}
            {isLoading && <div className="chat-msg assistant typing">导师正在思考...</div>}
            <div ref={chatEndRef} />
          </div>

          <div className="chat-input-area">
            <button onClick={handleRequestHint} className="btn-hint" title="请求提示">
              <Lightbulb size={16} />
            </button>
            <input
              type="text"
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleChatSend()}
              placeholder="向AI导师提问..."
              className="chat-input"
            />
            <button onClick={handleChatSend} disabled={isLoading} className="btn-send">
              <Send size={16} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
