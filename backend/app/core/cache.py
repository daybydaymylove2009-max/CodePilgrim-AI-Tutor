from __future__ import annotations

import json
import time
from typing import Any

import redis.asyncio as aioredis
from loguru import logger

from app.core.config import settings


class InMemoryFallback:
    def __init__(self):
        self._store: dict[str, tuple[Any, float | None]] = {}

    def _cleanup(self) -> None:
        now = time.time()
        expired = [k for k, (_, exp) in self._store.items() if exp is not None and now > exp]
        for k in expired:
            del self._store[k]

    async def get(self, key: str) -> Any | None:
        self._cleanup()
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expire = entry
        if expire is not None and time.time() > expire:
            del self._store[key]
            return None
        return value

    async def set(self, key: str, value: Any, expire: int | None = None) -> bool:
        exp = time.time() + expire if expire else None
        self._store[key] = (value, exp)
        return True

    async def delete(self, key: str) -> bool:
        self._store.pop(key, None)
        return True

    async def exists(self, key: str) -> bool:
        self._cleanup()
        return key in self._store

    async def incr(self, key: str) -> int:
        self._cleanup()
        entry = self._store.get(key)
        current = entry[0] if entry else 0
        current = int(current) + 1
        exp = entry[1] if entry else None
        self._store[key] = (current, exp)
        return current

    async def expire(self, key: str, seconds: int) -> bool:
        entry = self._store.get(key)
        if entry is None:
            return False
        self._store[key] = (entry[0], time.time() + seconds)
        return True

    async def ping(self) -> bool:
        return True

    async def close(self) -> None:
        self._store.clear()


class RedisService:
    def __init__(self):
        self._client: aioredis.Redis | None = None
        self._fallback: InMemoryFallback | None = None
        self._use_fallback: bool = False

    async def _ensure_client(self) -> None:
        if self._use_fallback:
            return
        if self._client is not None:
            return
        try:
            self._client = aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
            )
            await self._client.ping()
            logger.info("Redis connected successfully")
        except Exception as e:
            logger.warning(f"Redis connection failed ({e}), falling back to in-memory store")
            self._use_fallback = True
            self._fallback = InMemoryFallback()

    @property
    def fallback(self) -> InMemoryFallback:
        if self._fallback is None:
            self._fallback = InMemoryFallback()
        return self._fallback

    async def get(self, key: str) -> Any | None:
        try:
            await self._ensure_client()
            if self._use_fallback:
                return await self.fallback.get(key)
            value = await self._client.get(key)
            if value is None:
                return None
            return json.loads(value)
        except Exception as e:
            logger.warning(f"Redis GET failed for key={key}: {e}, using fallback")
            return await self.fallback.get(key)

    async def set(self, key: str, value: Any, expire: int | None = None) -> bool:
        try:
            await self._ensure_client()
            if self._use_fallback:
                return await self.fallback.set(key, value, expire)
            serialized = json.dumps(value, default=str)
            if expire:
                await self._client.setex(key, expire, serialized)
            else:
                await self._client.set(key, serialized)
            return True
        except Exception as e:
            logger.warning(f"Redis SET failed for key={key}: {e}, using fallback")
            return await self.fallback.set(key, value, expire)

    async def delete(self, key: str) -> bool:
        try:
            await self._ensure_client()
            if self._use_fallback:
                return await self.fallback.delete(key)
            await self._client.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Redis DELETE failed for key={key}: {e}, using fallback")
            return await self.fallback.delete(key)

    async def exists(self, key: str) -> bool:
        try:
            await self._ensure_client()
            if self._use_fallback:
                return await self.fallback.exists(key)
            return bool(await self._client.exists(key))
        except Exception as e:
            logger.warning(f"Redis EXISTS failed for key={key}: {e}, using fallback")
            return await self.fallback.exists(key)

    async def incr(self, key: str) -> int:
        try:
            await self._ensure_client()
            if self._use_fallback:
                return await self.fallback.incr(key)
            return await self._client.incr(key)
        except Exception as e:
            logger.warning(f"Redis INCR failed for key={key}: {e}, using fallback")
            return await self.fallback.incr(key)

    async def expire(self, key: str, seconds: int) -> bool:
        try:
            await self._ensure_client()
            if self._use_fallback:
                return await self.fallback.expire(key, seconds)
            return await self._client.expire(key, seconds)
        except Exception as e:
            logger.warning(f"Redis EXPIRE failed for key={key}: {e}, using fallback")
            return await self.fallback.expire(key, seconds)

    async def ping(self) -> bool:
        try:
            await self._ensure_client()
            if self._use_fallback:
                return await self.fallback.ping()
            return await self._client.ping()
        except Exception:
            return False

    async def close(self):
        if self._client:
            await self._client.close()
        if self._fallback:
            await self._fallback.close()


redis_service = RedisService()
