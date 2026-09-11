# Ledger Market

Ledger Market is a FastAPI/PostgreSQL marketplace backend with inventory-backed
listings, idempotent Stripe checkout, verified webhook ingestion, Redis retries,
and a double-entry payment ledger.

## Start the stack

```bash
cp .env.example .env
docker compose up --build
```

For local tests:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
pytest -q
```

Create a listing and checkout:

```bash
curl -X POST http://localhost:8000/listings \
  -H 'content-type: application/json' \
  -d '{"seller_id":"seller-1","title":"Mechanical keyboard","price_cents":8900,"inventory":2}'

curl -X POST http://localhost:8000/checkout \
  -H 'content-type: application/json' \
  -H 'idempotency-key: cart-2026-0001' \
  -d '{"listing_id":"LISTING_ID","buyer_id":"buyer-1"}'
```

Use Stripe CLI to forward signed test events to
`http://localhost:8000/webhooks/stripe`. The API acknowledges valid events after
queueing; the worker owns order transitions and ledger writes.

## Repository map

```text
app/api.py          REST endpoints and signature verification
app/checkout.py     inventory reservation and idempotency
app/webhooks.py     exactly-once event processing
app/ledger.py       balanced transfer writer
app/queue.py        Redis retry and dead-letter scheduling
tests/              80 parameterized pytest cases
loadtest/           Locust workload
docs/               architecture, invariants, and test plan
```

No benchmark result is bundled. Use the included workload against a named
environment before making throughput or latency claims.

