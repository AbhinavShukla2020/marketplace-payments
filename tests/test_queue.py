import json

from app.queue import WebhookQueue


class FakeRedis:
    def __init__(self):
        self.scheduled = []
        self.dead = []

    async def zadd(self, key, values):
        self.scheduled.append((key, values))

    async def lpush(self, key, value):
        self.dead.append((key, value))


async def test_retry_reschedules_with_incremented_attempt():
    redis = FakeRedis()
    queue = WebhookQueue(redis, max_attempts=4)
    await queue.retry({"id": "evt_1"}, 0)
    payload = json.loads(next(iter(redis.scheduled[0][1])))
    assert payload["attempt"] == 1


async def test_last_retry_goes_to_dead_letter_queue():
    redis = FakeRedis()
    queue = WebhookQueue(redis, max_attempts=3)
    await queue.retry({"id": "evt_2"}, 2)
    assert json.loads(redis.dead[0][1])["id"] == "evt_2"

