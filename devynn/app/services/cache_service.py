"""
Redis cache service for LLM output caching.
"""
import hashlib
import json
import logging

import redis.asyncio as aioredis
from app.core.config import settings

logger = logging.getLogger(__name__)

class CacheService:
    def __init__(self):
        self._r = None
        
    async def connect(self):
        self._r = await aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        logger.info("Connected to Redis Cache")

    def _key(self, domain: str, transcript: str) -> str:
        h = hashlib.sha256(f"{domain}:{transcript.strip().lower()}".encode()).hexdigest()
        return "devynn:llm:" + h

    async def get(self, domain: str, transcript: str): 
        raw = await self._r.get(self._key(domain, transcript))
        return json.loads(raw) if raw else None

    async def set(self, domain: str, transcript: str, data: dict, ttl: int = 3600):
        await self._r.setex(self._key(domain, transcript), ttl, json.dumps(data))

    async def flush(self):
        keys = await self._r.keys("devynn:llm:*")
        if keys:
            await self._r.delete(*keys)
