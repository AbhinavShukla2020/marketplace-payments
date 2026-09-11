from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Protocol

import stripe


@dataclass(frozen=True)
class PaymentIntent:
    intent_id: str
    client_secret: str
    status: str


class PaymentGateway(Protocol):
    async def create_intent(
        self, *, amount_cents: int, currency: str, order_id: str, idempotency_key: str
    ) -> PaymentIntent: ...

    def verify_webhook(self, payload: bytes, signature: str) -> dict: ...


class StripeGateway:
    def __init__(self, api_key: str, webhook_secret: str) -> None:
        self.client = stripe.StripeClient(api_key)
        self.webhook_secret = webhook_secret

    async def create_intent(
        self, *, amount_cents: int, currency: str, order_id: str, idempotency_key: str
    ) -> PaymentIntent:
        def create():
            return self.client.payment_intents.create(
                params={
                    "amount": amount_cents,
                    "currency": currency,
                    "metadata": {"order_id": order_id},
                    "automatic_payment_methods": {"enabled": True},
                },
                options={"idempotency_key": idempotency_key},
            )

        result = await asyncio.to_thread(create)
        return PaymentIntent(result.id, result.client_secret, result.status)

    def verify_webhook(self, payload: bytes, signature: str) -> dict:
        return stripe.Webhook.construct_event(payload, signature, self.webhook_secret)

