from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass


def stable_hash(payload: dict) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class LedgerPosting:
    account: str
    amount_cents: int


def sale_postings(
    order_id: str, seller_id: str, amount_cents: int, fee_bps: int
) -> list[LedgerPosting]:
    if amount_cents <= 0:
        raise ValueError("sale amount must be positive")
    if not 0 <= fee_bps <= 10_000:
        raise ValueError("fee_bps must be between 0 and 10000")
    fee = amount_cents * fee_bps // 10_000
    seller_amount = amount_cents - fee
    postings = [
        LedgerPosting(f"stripe_receivable:{order_id}", amount_cents),
        LedgerPosting(f"seller_payable:{seller_id}", -seller_amount),
        LedgerPosting("platform_revenue", -fee),
    ]
    if sum(posting.amount_cents for posting in postings) != 0:
        raise AssertionError("unbalanced sale postings")
    return postings

