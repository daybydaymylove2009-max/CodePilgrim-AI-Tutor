import { useState, useRef, useCallback, useEffect } from "react";
import { ShieldCheck, RefreshCw } from "lucide-react";
import { authApi } from "../../api";

interface SliderCaptchaProps {
  onVerified: (token: string) => void;
  onError: (message: string) => void;
}

export default function SliderCaptcha({ onVerified, onError }: SliderCaptchaProps) {
  const [captchaId, setCaptchaId] = useState("");
  const [targetPosition, setTargetPosition] = useState(0);
  const [sliderPos, setSliderPos] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const [isVerified, setIsVerified] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [isFailed, setIsFailed] = useState(false);
  const trackRef = useRef<HTMLDivElement>(null);
  const startXRef = useRef(0);

  const loadChallenge = useCallback(async () => {
    try {
      const { data } = await authApi.getCaptchaChallenge();
      setCaptchaId(data.captcha_id);
      setTargetPosition(data.target_position);
      setSliderPos(0);
      setIsVerified(false);
      setIsFailed(false);
    } catch {
      onError("获取验证码失败，请刷新重试");
    }
  }, [onError]);

  useEffect(() => {
    loadChallenge();
  }, [loadChallenge]);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (isVerified) return;
    setIsDragging(true);
    startXRef.current = e.clientX - sliderPos;
  }, [isVerified, sliderPos]);

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (!isDragging || isVerified) return;
      const track = trackRef.current;
      if (!track) return;
      const trackWidth = track.offsetWidth - 44;
      const newPos = Math.max(0, Math.min(e.clientX - startXRef.current, trackWidth));
      setSliderPos(newPos);
    },
    [isDragging, isVerified]
  );

  const handleMouseUp = useCallback(async () => {
    if (!isDragging || isVerified) return;
    setIsDragging(false);
    setIsVerifying(true);

    try {
      const { data } = await authApi.verifyCaptcha({
        captcha_id: captchaId,
        slider_position: Math.round(sliderPos),
      });

      if (data.success && data.captcha_token) {
        setIsVerified(true);
        onVerified(data.captcha_token);
      } else {
        setIsFailed(true);
        onError(data.message || "验证失败，请重试");
        setTimeout(() => {
          loadChallenge();
        }, 1500);
      }
    } catch {
      setIsFailed(true);
      onError("验证请求失败，请重试");
      setTimeout(loadChallenge, 1500);
    } finally {
      setIsVerifying(false);
    }
  }, [isDragging, isVerified, captchaId, sliderPos, onVerified, onError, loadChallenge]);

  const sliderTrackWidth = 300;
  const sliderButtonLeft = sliderPos;
  const fillWidth = sliderPos;
  const indicatorLeft = (targetPosition / sliderTrackWidth) * 100;

  return (
    <div className="slider-captcha">
      <div className="captcha-track-container">
        <div className="captcha-visual-track" ref={trackRef}>
          <div
            className="captcha-target-indicator"
            style={{ left: `${indicatorLeft}%` }}
          />
          <div
            className="captcha-slider-fill"
            style={{ width: `${fillWidth}px` }}
          />
          <div
            className={`captcha-slider-button ${
              isVerified ? "verified" : isFailed ? "failed" : isDragging ? "dragging" : ""
            }`}
            style={{ left: `${sliderButtonLeft}px` }}
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
        </div>
        <div className="captcha-hint">
          {isVerified
            ? "验证通过 ✓"
            : isFailed
            ? "验证失败，重新加载中..."
            : isVerifying
            ? "验证中..."
            : "请拖动滑块完成验证"}
        </div>
      </div>
      <button
        className="captcha-refresh"
        onClick={loadChallenge}
        disabled={isVerified}
        title="刷新验证码"
      >
        <RefreshCw size={14} />
      </button>
    </div>
  );
}
