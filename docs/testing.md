# Testing and load procedure

The suite contains 80 collected pytest cases. Parameterized cases exercise money
amounts, fee rounding, invalid prices, inventory bounds, currency normalization,
hash stability, retry scheduling, and dead-letter behavior. Run it with:

```bash
pytest -q
```

Integration coverage should run PostgreSQL, Redis, and Stripe CLI test-mode
events. Useful cases include two concurrent requests with one idempotency key,
two buyers racing for the last unit, duplicate webhook delivery, a crash after
ledger insertion but before Redis acknowledgement, and signature rejection.

For load testing, seed `seeded-listing`, start API and worker containers, then
run `locust -f loadtest/locustfile.py`. Record request rate and p50/p95/p99
latency along with database pool size, API worker count, and Stripe stub latency.

