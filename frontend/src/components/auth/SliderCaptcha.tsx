import { useState, useRef, useCallback, useEffect } from "react";
import { ShieldCheck, RefreshCw } from "lucide-react";
import { authApi } from "../../api";

interface SliderCaptchaProps {
  onVerified: (token: string) => void;
  onError: (message: string) => void;
}

interface ChallengeData {
  captcha_id: string;
  background_image: string;
  puzzle_image: string;
  puzzle_y: number;
  width: number;
  height: number;
  puzzle_size: number;
}

type LoadState = "loading" | "ready" | "error";

export default function SliderCaptcha({ onVerified, onError }: SliderCaptchaProps) {
  const [challenge, setChallenge] = useState<ChallengeData | null>(null);
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [errorMsg, setErrorMsg] = useState("");
  const [sliderX, setSliderX] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const [isVerified, setIsVerified] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [isFailed, setIsFailed] = useState(false);
  const trackRef = useRef<HTMLDivElement>(null);
  const startXRef = useRef(0);
  const animFrameRef = useRef<number>(0);
  const currentXRef = useRef(0);

  const loadChallenge = useCallback(async () => {
    setLoadState("loading");
    setErrorMsg("");
    try {
      const { data } = await authApi.getCaptchaChallenge();
      setChallenge(data);
      setSliderX(0);
      currentXRef.current = 0;
      setIsVerified(false);
      setIsFailed(false);
      setLoadState("ready");
    } catch {
      setErrorMsg("获取验证码失败，请点击重试");
      setLoadState("error");
      onError("获取验证码失败，请点击重试");
    }
  }, [onError]);

  useEffect(() => {
    loadChallenge();
  }, [loadChallenge]);

  useEffect(() => {
    return () => {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    };
  }, []);

  const getSliderMaxX = useCallback(() => {
    if (!trackRef.current) return challenge ? challenge.width - 44 : 260;
    return trackRef.current.offsetWidth - 44;
  }, [challenge]);

  const updateSliderPosition = useCallback((clientX: number) => {
    if (!trackRef.current) return;
    const maxX = getSliderMaxX();
    const delta = clientX - startXRef.current;
    const newX = Math.max(0, Math.min(delta, maxX));
    currentXRef.current = newX;
    setSliderX(newX);
  }, [getSliderMaxX]);

  const handleDragStart = useCallback(
    (clientX: number) => {
      if (isVerified || !challenge) return;
      setIsDragging(true);
      startXRef.current = clientX - currentXRef.current;
    },
    [isVerified, challenge]
  );

  const handleDragMove = useCallback(
    (clientX: number) => {
      if (!isDragging || isVerified) return;
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
      animFrameRef.current = requestAnimationFrame(() => updateSliderPosition(clientX));
    },
    [isDragging, isVerified, updateSliderPosition]
  );

  const handleDragEnd = useCallback(async () => {
    if (!isDragging || isVerified || !challenge) return;
    setIsDragging(false);

    if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);

    setIsVerifying(true);

    const trackWidth = getSliderMaxX();
    const moveX = (currentXRef.current / trackWidth) * (challenge.width - challenge.puzzle_size);
    const puzzleX = Math.round(moveX + challenge.puzzle_size / 2);

    try {
      const { data } = await authApi.verifyCaptcha({
        captcha_id: challenge.captcha_id,
        slider_x: puzzleX,
        slider_y: challenge.puzzle_y,
      });

      if (data.success && data.captcha_token) {
        setIsVerified(true);
        onVerified(data.captcha_token);
      } else {
        setIsFailed(true);
        onError(data.message || "验证失败，请重试");
        setTimeout(() => loadChallenge(), 1500);
      }
    } catch {
      setIsFailed(true);
      onError("验证请求失败，请重试");
      setTimeout(loadChallenge, 1500);
    } finally {
      setIsVerifying(false);
    }
  }, [isDragging, isVerified, challenge, onVerified, onError, loadChallenge, getSliderMaxX]);

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      handleDragStart(e.clientX);
    },
    [handleDragStart]
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      handleDragMove(e.clientX);
    },
    [handleDragMove]
  );

  const handleMouseUp = useCallback(() => {
    handleDragEnd();
  }, [handleDragEnd]);

  const handleTouchStart = useCallback(
    (e: React.TouchEvent) => {
      e.preventDefault();
      const touch = e.touches[0];
      handleDragStart(touch.clientX);
    },
    [handleDragStart]
  );

  const handleTouchMove = useCallback(
    (e: React.TouchEvent) => {
      e.preventDefault();
      const touch = e.touches[0];
      handleDragMove(touch.clientX);
    },
    [handleDragMove]
  );

  const handleTouchEnd = useCallback(() => {
    handleDragEnd();
  }, [handleDragEnd]);

  const pieceMargin = challenge ? Math.floor(challenge.puzzle_size / 2) + 22 : 48;

  const moveX = challenge
    ? (currentXRef.current / getSliderMaxX()) * (challenge.width - challenge.puzzle_size)
    : 0;

  const statusClass = isVerified ? "verified" : isFailed ? "failed" : isDragging ? "dragging" : "";

  return (
    <div className="slider-captcha">
      {loadState === "loading" && (
        <div className="captcha-loading">
          <div className="captcha-spinner" />
          <span>加载验证码...</span>
        </div>
      )}

      {loadState === "error" && (
        <div className="captcha-error-box">
          <span className="captcha-error-text">{errorMsg}</span>
          <button className="captcha-error-retry" onClick={loadChallenge}>
            <RefreshCw size={14} /> 重试
          </button>
        </div>
      )}

      {loadState === "ready" && challenge && (
        <div className="captcha-image-container">
          <div className="captcha-background-wrapper">
            <img
              src={`data:image/png;base64,${challenge.background_image}`}
              alt="captcha background"
              className="captcha-background-img"
              draggable={false}
            />
            <img
              src={`data:image/png;base64,${challenge.puzzle_image}`}
              alt="captcha puzzle"
              className={`captcha-puzzle-img ${statusClass}`}
              draggable={false}
              style={{
                top: challenge.puzzle_y - Math.floor(challenge.puzzle_size / 2) - pieceMargin,
                left: moveX - pieceMargin,
              }}
            />
            {isFailed && <div className="captcha-fail-overlay" />}
            {isVerified && (
              <div className="captcha-success-overlay">
                <div className="captcha-success-content">
                  <ShieldCheck size={36} />
                  <span>验证通过</span>
                </div>
              </div>
            )}
          </div>

          <div
            className="captcha-slider-track"
            ref={trackRef}
            onTouchStart={handleTouchStart}
            onTouchMove={handleTouchMove}
            onTouchEnd={handleTouchEnd}
          >
            <div
              className="captcha-slider-fill"
              style={{ width: `${sliderX + 22}px` }}
            />
            <div
              className={`captcha-slider-button ${statusClass}`}
              style={{ left: `${sliderX}px` }}
              onMouseDown={handleMouseDown}
              onMouseMove={isDragging ? handleMouseMove : undefined}
              onMouseUp={handleMouseUp}
              onMouseLeave={isDragging ? handleMouseUp : undefined}
              onTouchStart={handleTouchStart}
              onTouchMove={handleTouchMove}
              onTouchEnd={handleTouchEnd}
            >
              {isVerified ? (
                <ShieldCheck size={20} />
              ) : isFailed ? (
                <span className="captcha-icon-fail">✕</span>
              ) : (
                <span className="captcha-icon-arrow">⟫</span>
              )}
            </div>
            <span className="captcha-track-hint">
              {isVerified
                ? "验证通过 ✓"
                : isFailed
                  ? "验证失败，请重试"
                  : isVerifying
                    ? "验证中..."
                    : "→ 拖动滑块完成拼图验证 →"}
            </span>
          </div>
        </div>
      )}

      <button
        className="captcha-refresh"
        onClick={loadChallenge}
        disabled={isVerified || loadState === "loading"}
        title="刷新验证码"
      >
        <RefreshCw size={14} className={loadState === "loading" ? "spinning" : ""} />
      </button>
    </div>
  );
}
