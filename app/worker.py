from __future__ import annotations

import asyncio

from redis.asyncio import Redis

from .config import Settings
from .database import create_database
from .queue import WebhookQueue
from .webhooks import WebhookProcessor


async def run_worker(settings: Settings | None = None) -> None:
    settings = settings or Settings()
    engine, sessions = create_database(settings.database_url)
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    queue = WebhookQueue(redis, settings.webhook_max_attempts)
    processor = WebhookProcessor(sessions, settings.platform_fee_bps)
    try:
        while True:
            event, attempt = await queue.next()
            try:
                await processor.process(event)
            except Exception:
                await queue.retry(event, attempt)
    finally:
        await redis.aclose()
        await engine.dispose()


def main() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()

