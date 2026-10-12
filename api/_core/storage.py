"""Хранилище: Upstash Redis (REST) на проде, память процесса локально."""
from __future__ import annotations

import json
import os
import time
from typing import Any


class MemoryStore:
    def __init__(self) -> None:
        self._data: dict[str, tuple[Any, float | None]] = {}

    def _alive(self, key: str) -> bool:
        item = self._data.get(key)
        if item is None:
            return False
        if item[1] is not None and item[1] < time.time():
            del self._data[key]
            return False
        return True

    async def get_json(self, key: str) -> Any:
        return json.loads(self._data[key][0]) if self._alive(key) else None

    async def set_json(self, key: str, value: Any, ex: int | None = None) -> None:
        self._data[key] = (json.dumps(value, ensure_ascii=False), time.time() + ex if ex else None)

    async def delete(self, key: str) -> None:
        self._data.pop(key, None)

    async def incr(self, key: str, ex: int) -> int:
        value = int(self._data[key][0]) + 1 if self._alive(key) else 1
        expires = self._data[key][1] if self._alive(key) else time.time() + ex
        self._data[key] = (str(value), expires)
        return value


class UpstashStore:
    def __init__(self, url: str, token: str) -> None:
        from upstash_redis.asyncio import Redis

        self._r = Redis(url=url, token=token)

    async def get_json(self, key: str) -> Any:
        raw = await self._r.get(key)
        return json.loads(raw) if raw else None

    async def set_json(self, key: str, value: Any, ex: int | None = None) -> None:
        await self._r.set(key, json.dumps(value, ensure_ascii=False), ex=ex)

    async def delete(self, key: str) -> None:
        await self._r.delete(key)

    async def incr(self, key: str, ex: int) -> int:
        value = await self._r.incr(key)
        if value == 1:
            await self._r.expire(key, ex)
        return value


_store = None


def get_store():
    global _store
    if _store is None:
        url = os.getenv("KV_REST_API_URL") or os.getenv("UPSTASH_REDIS_REST_URL")
        token = os.getenv("KV_REST_API_TOKEN") or os.getenv("UPSTASH_REDIS_REST_TOKEN")
        _store = UpstashStore(url, token) if url and token else MemoryStore()
    return _store
