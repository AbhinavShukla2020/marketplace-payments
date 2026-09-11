# Architecture

The API owns listings, inventory reservations, orders, and idempotency records in
PostgreSQL. Checkout locks both the idempotency key and listing row under a
serializable transaction before decrementing inventory. It passes a derived key
to Stripe as well, so a repeated provider call cannot create a second intent.

Stripe webhook signatures are verified in the request process, but business
logic runs in a separate worker. Valid events enter a Redis sorted set. Failed
work is scheduled with exponential backoff and eventually moved to a dead-letter
list. The event ID is also the PostgreSQL primary key, making delivery idempotent
even if Redis redelivers after a worker crash.

Successful payments create three ledger lines in one database transaction: a
positive Stripe receivable, a negative seller payable, and negative platform
revenue. Lines for a transfer always sum to zero. This convention treats positive
amounts as debits and negative amounts as credits.

