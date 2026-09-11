from __future__ import annotations

from sqlalchemy import func, select

from .domain import LedgerPosting, sale_postings
from .models import LedgerLine


class Ledger:
    async def post(
        self,
        session,
        *,
        transfer_id: str,
        currency: str,
        postings: list[LedgerPosting],
        metadata: dict | None = None,
    ) -> None:
        if not postings or sum(posting.amount_cents for posting in postings) != 0:
            raise ValueError("ledger transfer must balance to zero")
        for posting in postings:
            session.add(
                LedgerLine(
                    transfer_id=transfer_id,
                    account=posting.account,
                    amount_cents=posting.amount_cents,
                    currency=currency,
                    metadata_json=metadata or {},
                )
            )

    async def post_sale(
        self, session, *, order_id: str, seller_id: str, amount_cents: int, currency: str, fee_bps: int
    ) -> None:
        await self.post(
            session,
            transfer_id=f"sale:{order_id}",
            currency=currency,
            postings=sale_postings(order_id, seller_id, amount_cents, fee_bps),
            metadata={"order_id": order_id},
        )

    async def transfer_balance(self, session, transfer_id: str) -> int:
        query = select(func.coalesce(func.sum(LedgerLine.amount_cents), 0)).where(
            LedgerLine.transfer_id == transfer_id
        )
        return int(await session.scalar(query))

