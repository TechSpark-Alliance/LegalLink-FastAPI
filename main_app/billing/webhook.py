from datetime import datetime

from fastapi import APIRouter, HTTPException, Request
import stripe

from main_app.core.config import settings

router = APIRouter(prefix="/billing", tags=["billing"])


def _build_subscription_payload(subscription: dict) -> dict:
    items = (subscription or {}).get("items", {}).get("data", [])
    price_id = None
    if items:
        price = items[0].get("price") or {}
        price_id = price.get("id")
    return {
        "id": subscription.get("id"),
        "status": subscription.get("status"),
        "price_id": price_id,
        "current_period_end": subscription.get("current_period_end"),
        "cancel_at_period_end": subscription.get("cancel_at_period_end"),
        "trial_end": subscription.get("trial_end"),
    }


async def _update_subscription(db, customer_id: str, subscription: dict) -> None:
    if not customer_id:
        return
    await db.users.update_one(
        {"stripe_customer_id": customer_id},
        {"$set": {"subscription": subscription, "updated_at": datetime.utcnow()}},
    )


@router.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing Stripe signature header")

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=settings.stripe_webhook_secret,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid payload") from exc
    except stripe.error.SignatureVerificationError as exc:
        raise HTTPException(status_code=400, detail="Invalid signature") from exc

    event_type = event.get("type", "")
    data_object = event.get("data", {}).get("object", {})
    db = request.app.mongodb

    if settings.stripe_secret_key:
        stripe.api_key = settings.stripe_secret_key

    if event_type == "checkout.session.completed":
        if data_object.get("mode") == "subscription":
            customer_id = data_object.get("customer")
            subscription_id = data_object.get("subscription")
            if subscription_id and settings.stripe_secret_key:
                subscription = stripe.Subscription.retrieve(subscription_id)
                payload = _build_subscription_payload(subscription)
                await _update_subscription(db, customer_id, payload)
    elif event_type in {
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    }:
        customer_id = data_object.get("customer")
        payload = _build_subscription_payload(data_object)
        await _update_subscription(db, customer_id, payload)
    elif event_type in {"invoice.paid", "invoice.payment_failed"}:
        customer_id = data_object.get("customer")
        subscription_id = data_object.get("subscription")
        if subscription_id and settings.stripe_secret_key:
            subscription = stripe.Subscription.retrieve(subscription_id)
            payload = _build_subscription_payload(subscription)
            await _update_subscription(db, customer_id, payload)

    return {"status": "ok", "type": event["type"]}
