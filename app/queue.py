from __future__ import annotations

import asyncio
import json
import time


class WebhookQueue:
    key = "market:webhooks"
    dead_letter_key = "market:webhooks:dead"

    def __init__(self, redis, max_attempts: int = 8) -> None:
        self.redis = redis
        self.max_attempts = max_attempts

    async def enqueue(self, event: dict, *, attempt: int = 0, delay: float = 0) -> None:
        item = json.dumps({"event": event, "attempt": attempt}, separators=(",", ":"))
        await self.redis.zadd(self.key, {item: time.time() + delay})

    async def next(self) -> tuple[dict, int]:
        while True:
            values = await self.redis.zpopmin(self.key, 1)
            if not values:
                await asyncio.sleep(0.1)
                continue
            raw, ready_at = values[0]
            wait = float(ready_at) - time.time()
            if wait > 0:
                await self.redis.zadd(self.key, {raw: ready_at})
                await asyncio.sleep(min(wait, 0.5))
                continue
            payload = json.loads(raw)
            return payload["event"], int(payload["attempt"])

    async def retry(self, event: dict, attempt: int) -> None:
        next_attempt = attempt + 1
        if next_attempt >= self.max_attempts:
            await self.redis.lpush(self.dead_letter_key, json.dumps(event))
            return
        await self.enqueue(event, attempt=next_attempt, delay=min(2**next_attempt, 60))

