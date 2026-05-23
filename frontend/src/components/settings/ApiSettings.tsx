import { useState, useEffect } from "react";
import { apiConfigApi } from "../../api";
import { Settings, Key, Eye, EyeOff, Check, X, Loader2, AlertTriangle, Activity } from "lucide-react";
import "./ApiSettings.css";

const PROVIDER_OPTIONS = [
  { value: "openai", label: "OpenAI" },
  { value: "anthropic", label: "Anthropic" },
  { value: "custom", label: "Custom (OpenAI-compatible)" },
];

const PROVIDER_DEFAULTS: Record<string, { api_base_url: string; model_name: string; placeholder: string }> = {
  openai: { api_base_url: "https://api.openai.com/v1", model_name: "gpt-4o", placeholder: "sk-..." },
  anthropic: { api_base_url: "https://api.anthropic.com", model_name: "claude-sonnet-4-20250514", placeholder: "sk-ant-..." },
  custom: { api_base_url: "", model_name: "", placeholder: "Enter your API key" },
};

interface ApiConfig {
  id: string;
  provider: string;
  api_key: string;
  api_base_url: string;
  model_name: string;
  is_active: boolean;
}

interface UsageData {
  total_calls: number;
  success_rate: number;
  avg_latency_ms: number;
  total_tokens: number;
  recent_calls: {
    id: string;
    endpoint: string;
    status: string;
    latency_ms: number;
    tokens_used: number;
    created_at: string;
  }[];
}

export default function ApiSettings() {
  const [config, setConfig] = useState<ApiConfig | null>(null);
  const [provider, setProvider] = useState("openai");
  const [apiKey, setApiKey] = useState("");
  const [apiBaseUrl, setApiBaseUrl] = useState("");
  const [modelName, setModelName] = useState("");
  const [isActive, setIsActive] = useState(true);
  const [showKey, setShowKey] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string; latency_ms?: number } | null>(null);
  const [usage, setUsage] = useState<UsageData | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);

  useEffect(() => {
    loadConfig();
    loadUsage();
  }, []);

  const loadConfig = async () => {
    try {
      const { data } = await apiConfigApi.getConfig();
      if (data) {
        setConfig(data);
        setProvider(data.provider || "openai");
        setApiKey(data.api_key || "");
        setApiBaseUrl(data.api_base_url || "");
        setModelName(data.model_name || "");
        setIsActive(data.is_active !== false);
      }
    } catch {
    } finally {
      setLoading(false);
    }
  };

  const loadUsage = async () => {
    try {
      const { data } = await apiConfigApi.getUsage();
      setUsage(data);
    } catch {
    }
  };

  const handleProviderChange = (newProvider: string) => {
    setProvider(newProvider);
    const defaults = PROVIDER_DEFAULTS[newProvider];
    if (!config || config.provider !== newProvider) {
      setApiBaseUrl(defaults.api_base_url);
      setModelName(defaults.model_name);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const payload = { provider, api_key: apiKey, api_base_url: apiBaseUrl || undefined, model_name: modelName || undefined };
      if (config) {
        await apiConfigApi.updateConfig({ ...payload, is_active: isActive });
      } else {
        await apiConfigApi.createConfig(payload);
      }
      await loadConfig();
      setTestResult(null);
    } catch (err: any) {
      setTestResult({ success: false, message: err?.response?.data?.detail || "保存失败" });
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await apiConfigApi.deleteConfig();
      setConfig(null);
      setApiKey("");
      setApiBaseUrl("");
      setModelName("");
      setIsActive(true);
      setProvider("openai");
      setConfirmDelete(false);
      setTestResult(null);
    } catch {
    } finally {
      setDeleting(false);
    }
  };

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const payload = apiKey ? { provider, api_key: apiKey, api_base_url: apiBaseUrl || undefined, model_name: modelName || undefined } : undefined;
      const { data } = await apiConfigApi.testConnection(payload);
      setTestResult({ success: data.success, message: data.message || (data.success ? "连接成功" : "连接失败"), latency_ms: data.latency_ms });
    } catch (err: any) {
      setTestResult({ success: false, message: err?.response?.data?.detail || "测试失败" });
    } finally {
      setTesting(false);
    }
  };

  const defaults = PROVIDER_DEFAULTS[provider];

  if (loading) {
    return (
      <div className="api-settings-page">
        <div className="api-settings-loading"><Loader2 size={24} className="spinning" /> 加载配置中...</div>
      </div>
    );
  }

  return (
    <div className="api-settings-page">
      <div className="api-settings-header">
        <div className="api-settings-title-row">
          <Settings size={24} />
          <h2>AI API 配置</h2>
        </div>
        <p className="api-settings-subtitle">每位用户使用自己的 API 密钥，确保数据隔离与隐私安全</p>
      </div>

      {!config && (
        <div className="api-status-banner warning">
          <AlertTriangle size={18} />
          <span>⚠️ 未配置个人 API 密钥，AI 功能将使用系统默认配置或降级为数据库回退模式</span>
        </div>
      )}
      {config && !isActive && (
        <div className="api-status-banner error">
          <X size={18} />
          <span>API 配置已禁用</span>
        </div>
      )}
      {config && isActive && (
        <div className="api-status-banner success">
          <Check size={18} />
          <span>✅ API 配置已激活 — {PROVIDER_OPTIONS.find(p => p.value === config.provider)?.label || config.provider}</span>
        </div>
      )}

      <div className="api-settings-card">
        <div className="api-settings-section">
          <h3><Key size={16} /> API 配置</h3>

          <div className="api-form-group">
            <label>提供商</label>
            <select className="api-select" value={provider} onChange={(e) => handleProviderChange(e.target.value)}>
              {PROVIDER_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>

          <div className="api-form-group">
            <label>API Key</label>
            <div className="api-key-input-wrapper">
              <input
                className="api-input"
                type={showKey ? "text" : "password"}
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder={defaults.placeholder}
              />
              <button className="btn-toggle-key" onClick={() => setShowKey(!showKey)} type="button">
                {showKey ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          <div className="api-form-group">
            <label>API Base URL {provider !== "custom" && <span className="api-label-hint">(可选，默认已填)</span>}</label>
            <input
              className="api-input"
              type="text"
              value={apiBaseUrl}
              onChange={(e) => setApiBaseUrl(e.target.value)}
              placeholder={defaults.api_base_url || "https://api.example.com/v1"}
            />
          </div>

          <div className="api-form-group">
            <label>模型名称 {provider !== "custom" && <span className="api-label-hint">(可选，默认已填)</span>}</label>
            <input
              className="api-input"
              type="text"
              value={modelName}
              onChange={(e) => setModelName(e.target.value)}
              placeholder={defaults.model_name || "model-name"}
            />
          </div>

          <div className="api-form-group api-form-row">
            <label>启用配置</label>
            <button
              className={`api-toggle ${isActive ? "active" : ""}`}
              onClick={() => setIsActive(!isActive)}
              type="button"
            >
              <span className="api-toggle-thumb" />
            </button>
          </div>
        </div>

        <div className="api-settings-section">
          <h3><Activity size={16} /> 连接测试</h3>
          <div className="api-test-row">
            <button className="btn-test" onClick={handleTest} disabled={testing || (!apiKey && !config)}>
              {testing ? <Loader2 size={14} className="spinning" /> : <Activity size={14} />}
              测试连接
            </button>
            {testResult && (
              <div className={`api-test-result ${testResult.success ? "success" : "error"}`}>
                {testResult.success ? <Check size={14} /> : <X size={14} />}
                <span>{testResult.message}</span>
                {testResult.latency_ms !== undefined && (
                  <span className="api-test-latency">{testResult.latency_ms}ms</span>
                )}
              </div>
            )}
          </div>
        </div>

        <div className="api-settings-actions">
          <button className="btn-save" onClick={handleSave} disabled={saving || !apiKey}>
            {saving ? <Loader2 size={14} className="spinning" /> : <Check size={14} />}
            保存配置
          </button>
          {config && (
            <>
              {!confirmDelete ? (
                <button className="btn-delete" onClick={() => setConfirmDelete(true)}>
                  <X size={14} />
                  删除配置
                </button>
              ) : (
                <div className="api-delete-confirm">
                  <span>确认删除？</span>
                  <button className="btn-delete" onClick={handleDelete} disabled={deleting}>
                    {deleting ? <Loader2 size={14} className="spinning" /> : <Check size={14} />}
                    确认
                  </button>
                  <button className="btn-cancel" onClick={() => setConfirmDelete(false)}>取消</button>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {usage && (
        <div className="api-settings-card">
          <div className="api-settings-section">
            <h3><Activity size={16} /> 使用统计</h3>
            <div className="api-usage-stats">
              <div className="api-usage-stat">
                <span className="api-usage-value">{usage.total_calls}</span>
                <span className="api-usage-label">总调用次数</span>
              </div>
              <div className="api-usage-stat">
                <span className="api-usage-value">{(usage.success_rate * 100).toFixed(1)}%</span>
                <span className="api-usage-label">成功率</span>
              </div>
              <div className="api-usage-stat">
                <span className="api-usage-value">{usage.avg_latency_ms}ms</span>
                <span className="api-usage-label">平均延迟</span>
              </div>
              <div className="api-usage-stat">
                <span className="api-usage-value">{usage.total_tokens}</span>
                <span className="api-usage-label">总 Tokens</span>
              </div>
            </div>

            {usage.recent_calls && usage.recent_calls.length > 0 && (
              <div className="api-usage-table-wrapper">
                <h4>最近调用记录</h4>
                <table className="api-usage-table">
                  <thead>
                    <tr>
                      <th>端点</th>
                      <th>状态</th>
                      <th>延迟</th>
                      <th>Tokens</th>
                      <th>时间</th>
                    </tr>
                  </thead>
                  <tbody>
                    {usage.recent_calls.slice(0, 10).map((call) => (
                      <tr key={call.id}>
                        <td className="api-table-endpoint">{call.endpoint}</td>
                        <td>
                          <span className={`api-table-status ${call.status === "success" ? "success" : "error"}`}>
                            {call.status === "success" ? "成功" : "失败"}
                          </span>
                        </td>
                        <td>{call.latency_ms}ms</td>
                        <td>{call.tokens_used}</td>
                        <td className="api-table-time">{new Date(call.created_at).toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
