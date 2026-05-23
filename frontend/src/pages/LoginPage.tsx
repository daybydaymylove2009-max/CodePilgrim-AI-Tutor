import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "../store";
import { BookOpen, Eye, EyeOff, Check, X } from "lucide-react";
import SliderCaptcha from "../components/auth/SliderCaptcha";

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState("");
  const [isRegister, setIsRegister] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [captchaToken, setCaptchaToken] = useState("");
  const [captchaError, setCaptchaError] = useState("");
  const navigate = useNavigate();
  const { login, register } = useAuthStore();

  const passwordStrength = (() => {
    if (!password) return 0;
    let score = 0;
    if (password.length >= 8) score++;
    if (password.length >= 12) score++;
    if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score++;
    if (/\d/.test(password)) score++;
    if (/[^a-zA-Z0-9]/.test(password)) score++;
    return Math.min(score, 4);
  })();

  const strengthLabels = ["", "弱", "一般", "强", "非常强"];
  const strengthColors = ["", "#ef4444", "#f97316", "#22c55e", "#6366f1"];

  const passwordsMatch = !isRegister || password === confirmPassword;
  const canSubmit =
    username &&
    password &&
    (!isRegister || (email && displayName && passwordsMatch && password.length >= 8)) &&
    captchaToken;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setCaptchaError("");

    if (!captchaToken) {
      setCaptchaError("请先完成滑块验证");
      return;
    }

    if (isRegister && password !== confirmPassword) {
      setError("两次输入的密码不一致");
      return;
    }

    try {
      if (isRegister) {
        await register({
          username,
          email,
          password,
          confirm_password: confirmPassword,
          display_name: displayName,
          captcha_token: captchaToken,
        });
      } else {
        await login(username, password);
      }
      navigate("/learn");
    } catch (err: unknown) {
      const resp = (err as { response?: { data?: { detail?: string; message?: string } } })?.response?.data;
      const msg = resp?.detail || resp?.message || "操作失败，请重试";
      setError(msg);
      setCaptchaToken("");
    }
  };

  return (
    <div className="login-page">
      <div className={`login-card ${isRegister ? "register-mode" : ""}`}>
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
              placeholder="字母、数字、下划线、中文"
              minLength={3}
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
            <div className="password-input-wrapper">
              <input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                placeholder={isRegister ? "至少8位，含大小写和数字" : "输入密码"}
                minLength={8}
              />
              <button
                type="button"
                className="btn-toggle-password"
                onClick={() => setShowPassword(!showPassword)}
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
            {isRegister && password && (
              <div className="password-strength">
                <div className="strength-bars">
                  {[1, 2, 3, 4].map((level) => (
                    <div
                      key={level}
                      className="strength-bar"
                      style={{
                        backgroundColor: passwordStrength >= level ? strengthColors[passwordStrength] : "#334155",
                      }}
                    />
                  ))}
                </div>
                <span className="strength-label" style={{ color: strengthColors[passwordStrength] }}>
                  {strengthLabels[passwordStrength]}
                </span>
              </div>
            )}
          </div>

          {isRegister && (
            <div className="form-group">
              <label>确认密码</label>
              <div className="password-input-wrapper">
                <input
                  type={showPassword ? "text" : "password"}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                  placeholder="再次输入密码"
                  minLength={8}
                  className={confirmPassword && !passwordsMatch ? "input-error" : ""}
                />
                {confirmPassword && (
                  <span className={`match-indicator ${passwordsMatch ? "match" : "mismatch"}`}>
                    {passwordsMatch ? <Check size={16} /> : <X size={16} />}
                  </span>
                )}
              </div>
              {confirmPassword && !passwordsMatch && (
                <span className="field-error">两次输入的密码不一致</span>
              )}
            </div>
          )}

          <div className="form-group">
            <label>安全验证</label>
            <SliderCaptcha
              onVerified={(token) => {
                setCaptchaToken(token);
                setCaptchaError("");
              }}
              onError={(msg) => setCaptchaError(msg)}
            />
            {captchaError && <span className="field-error">{captchaError}</span>}
          </div>

          <button type="submit" className="btn-primary" disabled={!canSubmit}>
            {isRegister ? "注册" : "登录"}
          </button>
        </form>

        <p className="toggle-text">
          {isRegister ? "已有账号？" : "没有账号？"}
          <button onClick={() => { setIsRegister(!isRegister); setError(""); setCaptchaToken(""); }} className="btn-link">
            {isRegister ? "去登录" : "去注册"}
          </button>
        </p>
      </div>
    </div>
  );
}
