import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "../store";
import { BookOpen } from "lucide-react";

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const navigate = useNavigate();
  const { login, register } = useAuthStore();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      if (isRegister) {
        await register({ username, email, password, display_name: displayName });
      } else {
        await login(username, password);
      }
      navigate("/learn");
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "操作失败，请重试";
      setError(msg);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-header">
          <BookOpen size={40} />
          <h1>CodePilgrim</h1>
          <p>Vibe 为帆，代码为舵</p>
        </div>

        <form onSubmit={handleSubmit}>
          {error && <div className="error-msg">{error}</div>}

          <div className="form-group">
            <label>用户名</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              placeholder="输入用户名"
            />
          </div>

          {isRegister && (
            <>
              <div className="form-group">
                <label>邮箱</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  placeholder="your@email.com"
                />
              </div>
              <div className="form-group">
                <label>显示名称</label>
                <input
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  required
                  placeholder="你希望被称呼的名字"
                />
              </div>
            </>
          )}

          <div className="form-group">
            <label>密码</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder="输入密码"
              minLength={8}
            />
          </div>

          <button type="submit" className="btn-primary">
            {isRegister ? "注册" : "登录"}
          </button>
        </form>

        <p className="toggle-text">
          {isRegister ? "已有账号？" : "没有账号？"}
          <button onClick={() => setIsRegister(!isRegister)} className="btn-link">
            {isRegister ? "去登录" : "去注册"}
          </button>
        </p>
      </div>
    </div>
  );
}
