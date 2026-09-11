from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field
from redis.asyncio import Redis
from sqlalchemy import select

from .checkout import CheckoutService, IdempotencyConflict, PaymentUnavailable
from .config import Settings
from .database import create_database, initialize
from .models import Listing, Order
from .payments import StripeGateway
from .queue import WebhookQueue


class ListingInput(BaseModel):
    seller_id: str = Field(min_length=1, max_length=32)
    title: str = Field(min_length=3, max_length=120)
    price_cents: int = Field(gt=0)
    currency: str = Field(default="usd", pattern="^[a-z]{3}$")
    inventory: int = Field(default=1, ge=1)


class CheckoutInput(BaseModel):
    listing_id: str
    buyer_id: str


def create_app(settings: Settings | None = None, payment_gateway=None) -> FastAPI:
    settings = settings or Settings()
    engine, sessions = create_database(settings.database_url)
    payments = payment_gateway or StripeGateway(
        settings.stripe_secret_key, settings.stripe_webhook_secret
    )
    checkout = CheckoutService(sessions, payments)
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    queue = WebhookQueue(redis, settings.webhook_max_attempts)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        await initialize(engine)
        yield
        await redis.aclose()
        await engine.dispose()

    app = FastAPI(title="Ledger Market", version="0.1.0", lifespan=lifespan)

    async def db_session():
        async with sessions() as session:
            yield session

    @app.post("/listings", status_code=201)
    async def create_listing(body: ListingInput, session=Depends(db_session)):
        listing = Listing(**body.model_dump())
        session.add(listing)
        await session.commit()
        return {
            "listing_id": listing.listing_id,
            "seller_id": listing.seller_id,
            "title": listing.title,
            "price_cents": listing.price_cents,
            "currency": listing.currency,
            "inventory": listing.inventory,
        }

    @app.get("/listings")
    async def listings(session=Depends(db_session)):
        rows = await session.scalars(select(Listing).where(Listing.inventory > 0))
        return [
            {
                "listing_id": row.listing_id,
                "seller_id": row.seller_id,
                "title": row.title,
                "price_cents": row.price_cents,
                "currency": row.currency,
                "inventory": row.inventory,
            }
            for row in rows
        ]

    @app.get("/orders/{order_id}")
    async def get_order(order_id: str, session=Depends(db_session)):
        order = await session.get(Order, order_id)
        if order is None:
            raise HTTPException(404, "order not found")
        return {
            "order_id": order.order_id,
            "listing_id": order.listing_id,
            "status": order.status,
            "amount_cents": order.amount_cents,
            "currency": order.currency,
        }

    @app.post("/checkout", status_code=201)
    async def create_checkout(
        body: CheckoutInput, idempotency_key: str = Header(min_length=8, max_length=80)
    ):
        try:
            return await checkout.checkout(
                listing_id=body.listing_id, buyer_id=body.buyer_id, key=idempotency_key
            )
        except KeyError as error:
            raise HTTPException(404, str(error)) from error
        except IdempotencyConflict as error:
            raise HTTPException(409, str(error)) from error
        except PaymentUnavailable as error:
            raise HTTPException(502, str(error)) from error
        except ValueError as error:
            raise HTTPException(422, str(error)) from error

    @app.post("/webhooks/stripe", status_code=202)
    async def stripe_webhook(request: Request, stripe_signature: str = Header(alias="stripe-signature")):
        raw = await request.body()
        try:
            event = payments.verify_webhook(raw, stripe_signature)
        except Exception as error:
            raise HTTPException(400, "invalid Stripe signature") from error
        await queue.enqueue(dict(event))
        return {"accepted": True, "event_id": event["id"]}

    return app


app = create_app()
