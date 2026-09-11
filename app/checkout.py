from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from .domain import stable_hash
from .models import IdempotencyRecord, Listing, Order
from .payments import PaymentGateway


class IdempotencyConflict(ValueError):
    pass


class PaymentUnavailable(RuntimeError):
    pass


class CheckoutService:
    def __init__(self, sessions, payments: PaymentGateway) -> None:
        self.sessions = sessions
        self.payments = payments

    async def checkout(self, *, listing_id: str, buyer_id: str, key: str) -> dict:
        request = {"listing_id": listing_id, "buyer_id": buyer_id}
        digest = stable_hash(request)
        async with self.sessions() as session:
            existing = await session.get(
                IdempotencyRecord, {"scope": "checkout", "key": key}, with_for_update=True
            )
            if existing:
                if existing.request_hash != digest:
                    raise IdempotencyConflict("idempotency key was used with a different request")
                if existing.response is not None:
                    if existing.status_code and existing.status_code >= 400:
                        raise PaymentUnavailable(existing.response["error"])
                    return existing.response
                raise IdempotencyConflict("checkout with this key is still in progress")

            listing = await session.scalar(
                select(Listing).where(Listing.listing_id == listing_id).with_for_update()
            )
            if listing is None:
                raise KeyError("listing not found")
            if listing.inventory <= 0:
                raise ValueError("listing is sold out")
            listing.inventory -= 1
            order = Order(
                listing_id=listing.listing_id,
                buyer_id=buyer_id,
                seller_id=listing.seller_id,
                amount_cents=listing.price_cents,
                currency=listing.currency,
            )
            record = IdempotencyRecord(scope="checkout", key=key, request_hash=digest)
            session.add_all([order, record])
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                return await self.checkout(listing_id=listing_id, buyer_id=buyer_id, key=key)

        try:
            intent = await self.payments.create_intent(
                amount_cents=order.amount_cents,
                currency=order.currency,
                order_id=order.order_id,
                idempotency_key=f"checkout:{key}",
            )
        except Exception as error:
            async with self.sessions() as session:
                retry_order = await session.get(Order, order.order_id, with_for_update=True)
                retry_listing = await session.get(Listing, listing_id, with_for_update=True)
                retry_record = await session.get(
                    IdempotencyRecord, {"scope": "checkout", "key": key}, with_for_update=True
                )
                retry_listing.inventory += 1
                retry_order.status = "failed"
                retry_record.status_code = 502
                retry_record.response = {
                    "error": "payment provider unavailable",
                    "order_id": order.order_id,
                }
                await session.commit()
            raise PaymentUnavailable("payment provider unavailable") from error

        response = {
            "order_id": order.order_id,
            "payment_intent_id": intent.intent_id,
            "client_secret": intent.client_secret,
            "status": intent.status,
        }
        async with self.sessions() as session:
            saved_order = await session.get(Order, order.order_id, with_for_update=True)
            saved_record = await session.get(
                IdempotencyRecord, {"scope": "checkout", "key": key}, with_for_update=True
            )
            saved_order.payment_intent_id = intent.intent_id
            saved_record.status_code = 201
            saved_record.response = response
            await session.commit()
        return response
