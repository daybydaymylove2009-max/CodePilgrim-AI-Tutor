from __future__ import annotations

import json
from typing import Any

import redis.asyncio as aioredis
from loguru import logger

from app.core.config import settings


class RedisService:
    def __init__(self):
        self._client: aioredis.Redis | None = None

    @property
    def client(self) -> aioredis.Redis:
        if self._client is None:
            self._client = aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._client

    async def get(self, key: str) -> Any | None:
        try:
            value = await self.client.get(key)
            if value is None:
                return None
            return json.loads(value)
        except Exception as e:
            logger.warning(f"Redis GET failed for key={key}: {e}")
            return None

    async def set(self, key: str, value: Any, expire: int | None = None) -> bool:
        try:
            serialized = json.dumps(value, default=str)
            if expire:
                await self.client.setex(key, expire, serialized)
            else:
                await self.client.set(key, serialized)
            return True
        except Exception as e:
            logger.warning(f"Redis SET failed for key={key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        try:
            await self.client.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Redis DELETE failed for key={key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        try:
            return bool(await self.client.exists(key))
        except Exception as e:
            logger.warning(f"Redis EXISTS failed for key={key}: {e}")
            return False

    async def incr(self, key: str) -> int:
        try:
            return await self.client.incr(key)
        except Exception as e:
            logger.warning(f"Redis INCR failed for key={key}: {e}")
            return 0

    async def expire(self, key: str, seconds: int) -> bool:
        try:
            return await self.client.expire(key, seconds)
        except Exception as e:
            logger.warning(f"Redis EXPIRE failed for key={key}: {e}")
            return False

    async def ping(self) -> bool:
        try:
            return await self.client.ping()
        except Exception:
            return False

    async def close(self):
        if self._client:
            await self._client.close()


redis_service = RedisService()
