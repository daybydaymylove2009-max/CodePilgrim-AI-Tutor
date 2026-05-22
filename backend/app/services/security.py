from __future__ import annotations

import time
import uuid
from typing import Any

from loguru import logger

from app.core.cache import redis_service
from app.services.captcha_generator import CaptchaGenerator, captcha_generator


class CaptchaService:
    """
    图形拼图验证码服务.

    流程：
    1. 客户端请求 /auth/captcha/challenge → 获取 captcha_id + 背景图 + 拼图块
    2. 用户拖动拼图块到正确位置，客户端提交 /auth/captcha/verify → 验证位置
    3. 验证通过后获得 captcha_token，用于注册请求

    独立可复用：CaptchaGenerator 可被任何进程直接调用
    """

    CAPTCHA_PREFIX = "captcha:"
    TOKEN_PREFIX = "captcha_token:"
    CAPTCHA_EXPIRE = 300
    TOKEN_EXPIRE = 600
    TOLERANCE = 8

    def __init__(self, generator: CaptchaGenerator | None = None):
        self._generator = generator or captcha_generator

    async def create_challenge(self) -> dict[str, Any]:
        captcha_id = str(uuid.uuid4())

        result = self._generator.generate()

        captcha_data = {
            "captcha_id": captcha_id,
            "puzzle_x": result.puzzle_x,
            "puzzle_y": result.puzzle_y,
            "created_at": time.time(),
        }
        await redis_service.set(
            f"{self.CAPTCHA_PREFIX}{captcha_id}",
            captcha_data,
            expire=self.CAPTCHA_EXPIRE,
        )

        return {
            "captcha_id": captcha_id,
            "background_image": result.background_b64,
            "puzzle_image": result.puzzle_b64,
            "puzzle_y": result.puzzle_y,
            "width": result.width,
            "height": result.height,
            "puzzle_size": result.puzzle_size,
        }

    async def verify_captcha(self, captcha_id: str, user_x: int, user_y: int) -> dict[str, Any]:
        captcha_data = await redis_service.get(f"{self.CAPTCHA_PREFIX}{captcha_id}")
        if not captcha_data:
            return {"success": False, "message": "验证码已过期，请重新获取"}

        created_at = captcha_data.get("created_at", 0)
        if time.time() - created_at > self.CAPTCHA_EXPIRE:
            await redis_service.delete(f"{self.CAPTCHA_PREFIX}{captcha_id}")
            return {"success": False, "message": "验证码已过期，请重新获取"}

        expected_x = captcha_data.get("puzzle_x", 0)
        expected_y = captcha_data.get("puzzle_y", 0)

        x_match = abs(user_x - expected_x) <= self.TOLERANCE
        y_match = abs(user_y - expected_y) <= self.TOLERANCE

        if x_match and y_match:
            captcha_token = str(uuid.uuid4())
            token_data = {
                "captcha_id": captcha_id,
                "verified_at": time.time(),
            }
            await redis_service.set(
                f"{self.TOKEN_PREFIX}{captcha_token}",
                token_data,
                expire=self.TOKEN_EXPIRE,
            )
            await redis_service.delete(f"{self.CAPTCHA_PREFIX}{captcha_id}")

            logger.info(f"Captcha verified: captcha_id={captcha_id}")
            return {"success": True, "captcha_token": captcha_token}
        else:
            await redis_service.delete(f"{self.CAPTCHA_PREFIX}{captcha_id}")
            return {"success": False, "message": "拼图位置不正确，请重试"}

    async def validate_token(self, captcha_token: str) -> bool:
        token_data = await redis_service.get(f"{self.TOKEN_PREFIX}{captcha_token}")
        if not token_data:
            return False
        await redis_service.delete(f"{self.TOKEN_PREFIX}{captcha_token}")
        return True


class AntiAbuseService:
    """
    防恶意注册服务.

    多层防护：
    1. IP频率限制 — 同一IP每分钟/每小时/每天注册次数上限
    2. 异常行为检测 — 短时间多次注册、用户名模式检测
    3. 可疑注册标记 — 触发人工审核或额外验证
    """

    IP_RATE_PREFIX = "ip_rate:"
    IP_DAILY_PREFIX = "ip_daily:"
    GLOBAL_HOURLY_PREFIX = "global_hourly:"
    SUSPICIOUS_PREFIX = "suspicious:"

    IP_PER_MINUTE = 2
    IP_PER_HOUR = 5
    IP_PER_DAY = 10
    GLOBAL_PER_HOUR = 100

    SUSPICIOUS_PATTERNS = [
        lambda u: u.isdigit(),
        lambda u: len(u) <= 4 and u.isalpha(),
        lambda u: any(seq in u.lower() for seq in ["test", "spam", "bot", "fake", "admin"]),
    ]

    async def check_ip_rate(self, client_ip: str) -> dict[str, Any]:
        minute_key = f"{self.IP_RATE_PREFIX}{client_ip}:minute"
        hour_key = f"{self.IP_RATE_PREFIX}{client_ip}:hour"
        day_key = f"{self.IP_DAILY_PREFIX}{client_ip}"

        minute_count = await redis_service.get(minute_key) or 0
        hour_count = await redis_service.get(hour_key) or 0
        day_count = await redis_service.get(day_key) or 0

        minute_count = int(minute_count) if minute_count else 0
        hour_count = int(hour_count) if hour_count else 0
        day_count = int(day_count) if day_count else 0

        if minute_count >= self.IP_PER_MINUTE:
            return {
                "allowed": False,
                "reason": "注册过于频繁，请1分钟后再试",
                "retry_after": 60,
            }
        if hour_count >= self.IP_PER_HOUR:
            return {
                "allowed": False,
                "reason": "该IP注册次数已达小时上限，请稍后再试",
                "retry_after": 3600,
            }
        if day_count >= self.IP_PER_DAY:
            return {
                "allowed": False,
                "reason": "该IP今日注册次数已达上限，请明天再试",
                "retry_after": 86400,
            }

        return {"allowed": True}

    async def record_registration(self, client_ip: str) -> None:
        minute_key = f"{self.IP_RATE_PREFIX}{client_ip}:minute"
        hour_key = f"{self.IP_RATE_PREFIX}{client_ip}:hour"
        day_key = f"{self.IP_DAILY_PREFIX}{client_ip}"

        await redis_service.incr(minute_key)
        await redis_service.expire(minute_key, 60)

        await redis_service.incr(hour_key)
        await redis_service.expire(hour_key, 3600)

        await redis_service.incr(day_key)
        await redis_service.expire(day_key, 86400)

        global_key = self.GLOBAL_HOURLY_PREFIX
        await redis_service.incr(global_key)
        await redis_service.expire(global_key, 3600)

    async def detect_suspicious(self, username: str, email: str, client_ip: str) -> dict[str, Any]:
        risk_score = 0
        flags = []

        for pattern in self.SUSPICIOUS_PATTERNS:
            if pattern(username):
                risk_score += 30
                flags.append(f"可疑用户名模式: {username}")
                break

        email_local = email.split("@")[0]
        if email_local.isdigit():
            risk_score += 20
            flags.append("纯数字邮箱前缀")

        ip_suspicious_key = f"{self.SUSPICIOUS_PREFIX}{client_ip}"
        ip_flag_count = await redis_service.get(ip_suspicious_key) or 0
        ip_flag_count = int(ip_flag_count) if ip_flag_count else 0
        if ip_flag_count >= 2:
            risk_score += 40
            flags.append("该IP存在多次可疑注册记录")

        is_suspicious = risk_score >= 50

        if is_suspicious:
            await redis_service.incr(ip_suspicious_key)
            await redis_service.expire(ip_suspicious_key, 86400)
            logger.warning(f"Suspicious registration detected: username={username}, ip={client_ip}, score={risk_score}, flags={flags}")

        return {
            "is_suspicious": is_suspicious,
            "risk_score": risk_score,
            "flags": flags,
            "action": "review" if risk_score >= 70 else ("extra_verify" if risk_score >= 50 else "allow"),
        }

    async def check_global_rate(self) -> bool:
        count = await redis_service.get(self.GLOBAL_HOURLY_PREFIX) or 0
        return int(count) < self.GLOBAL_PER_HOUR


captcha_service = CaptchaService()
anti_abuse_service = AntiAbuseService()
