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

export default function SliderCaptcha({ onVerified, onError }: SliderCaptchaProps) {
  const [challenge, setChallenge] = useState<ChallengeData | null>(null);
  const [sliderX, setSliderX] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const [isVerified, setIsVerified] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [isFailed, setIsFailed] = useState(false);
  const trackRef = useRef<HTMLDivElement>(null);
  const startXRef = useRef(0);

  const loadChallenge = useCallback(async () => {
    try {
      const { data } = await authApi.getCaptchaChallenge();
      setChallenge(data);
      setSliderX(0);
      setIsVerified(false);
      setIsFailed(false);
    } catch {
      onError("获取验证码失败，请刷新重试");
    }
  }, [onError]);

  useEffect(() => {
    loadChallenge();
  }, [loadChallenge]);

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (isVerified || !challenge) return;
      setIsDragging(true);
      startXRef.current = e.clientX - sliderX;
    },
    [isVerified, sliderX, challenge]
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (!isDragging || isVerified || !trackRef.current || !challenge) return;
      const trackWidth = trackRef.current.offsetWidth - 44;
      const newSliderX = Math.max(0, Math.min(e.clientX - startXRef.current, trackWidth));
      setSliderX(newSliderX);
    },
    [isDragging, isVerified, challenge]
  );

  const handleMouseUp = useCallback(async () => {
    if (!isDragging || isVerified || !challenge) return;
    setIsDragging(false);
    setIsVerifying(true);

    const trackWidth = trackRef.current?.offsetWidth ? trackRef.current.offsetWidth - 44 : 260;
    const maxX = challenge.width - challenge.puzzle_size;
    const ratio = maxX / trackWidth;
    const puzzleX = Math.round(sliderX * ratio);

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
  }, [isDragging, isVerified, challenge, sliderX, onVerified, onError, loadChallenge]);

  const puzzleOffsetX = challenge
    ? (sliderX / (trackRef.current ? trackRef.current.offsetWidth - 44 : 260)) *
      (challenge.width - challenge.puzzle_size)
    : 0;

  return (
    <div className="slider-captcha">
      {challenge && (
        <div className="captcha-image-container">
          <div className="captcha-background-wrapper" style={{ width: challenge.width, height: challenge.height }}>
            <img
              src={`data:image/png;base64,${challenge.background_image}`}
              alt="captcha background"
              className="captcha-background-img"
              draggable={false}
            />
            <img
              src={`data:image/png;base64,${challenge.puzzle_image}`}
              alt="captcha puzzle"
              className="captcha-puzzle-img"
              draggable={false}
              style={{
                top: challenge.puzzle_y - challenge.puzzle_size / 2 - 10,
                left: puzzleOffsetX - challenge.puzzle_size / 2 - 10,
              }}
            />
          </div>

          <div className="captcha-slider-track" ref={trackRef}>
            <div
              className="captcha-slider-fill"
              style={{ width: `${sliderX}px` }}
            />
            <div
              className={`captcha-slider-button ${
                isVerified ? "verified" : isFailed ? "failed" : isDragging ? "dragging" : ""
              }`}
              style={{ left: `${sliderX}px` }}
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              onMouseLeave={isDragging ? handleMouseUp : undefined}
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
              {isVerified ? "验证通过 ✓" : isFailed ? "验证失败" : isVerifying ? "验证中..." : "→ 拖动滑块完成拼图验证 →"}
            </span>
          </div>
        </div>
      )}

      <button className="captcha-refresh" onClick={loadChallenge} disabled={isVerified} title="刷新验证码">
        <RefreshCw size={14} />
      </button>
    </div>
  );
}
