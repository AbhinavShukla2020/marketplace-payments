from __future__ import annotations

import datetime as dt

from .ledger import Ledger
from .models import Order, WebhookEvent


class WebhookProcessor:
    def __init__(self, sessions, fee_bps: int) -> None:
        self.sessions = sessions
        self.fee_bps = fee_bps
        self.ledger = Ledger()

    async def process(self, event: dict) -> None:
        event_id = event["id"]
        async with self.sessions() as session:
            if await session.get(WebhookEvent, event_id):
                return
            saved = WebhookEvent(event_id=event_id, event_type=event["type"], payload=event)
            session.add(saved)
            if event["type"] == "payment_intent.succeeded":
                intent = event["data"]["object"]
                order_id = intent["metadata"]["order_id"]
                order = await session.get(Order, order_id, with_for_update=True)
                if order is None:
                    raise KeyError(f"order not found: {order_id}")
                if order.status != "paid":
                    order.status = "paid"
                    await self.ledger.post_sale(
                        session,
                        order_id=order.order_id,
                        seller_id=order.seller_id,
                        amount_cents=order.amount_cents,
                        currency=order.currency,
                        fee_bps=self.fee_bps,
                    )
            elif event["type"] == "payment_intent.payment_failed":
                intent = event["data"]["object"]
                order = await session.get(Order, intent["metadata"]["order_id"], with_for_update=True)
                if order:
                    order.status = "failed"
            saved.processed_at = dt.datetime.now(dt.timezone.utc)
            await session.commit()

