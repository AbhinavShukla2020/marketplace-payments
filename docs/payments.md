# Payment invariants

The code is organized around a few invariants that are easier to test than a
large collection of endpoint examples.

1. One checkout key maps to one request body and one stored response.
2. Inventory is decremented while the listing row is locked.
3. Stripe receives its own deterministic idempotency key.
4. A webhook event ID is processed at most once.
5. Every ledger transfer sums to zero in integer minor units.
6. Money never passes through floating-point arithmetic.

The checkout implementation reserves inventory before contacting Stripe. A
provider error marks the order failed and restores inventory. The idempotency
record keeps that result stable rather than creating a surprise second order.
Production systems often add an expiration policy so a buyer can intentionally
retry a provider outage with a new checkout key.

