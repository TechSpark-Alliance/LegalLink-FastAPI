from datetime import datetime

import stripe
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Request

from main_app.core.config import settings
from main_app.session_utils.session_functions import get_active_session
from models.billing import CheckoutSessionRequest

router = APIRouter(prefix="/billing", tags=["billing"])


def _get_stripe_client() -> None:
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=500, detail="Stripe secret key not configured")
    stripe.api_key = settings.stripe_secret_key


async def _get_user_from_request(request: Request) -> dict:
    auth_header = request.headers.get("Authorization", "")
    token = ""
    if auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1].strip()
    if not token:
        token = request.query_params.get("token", "")
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")

    db = request.app.mongodb
    session = await get_active_session(db, token)
    if not session:
        raise HTTPException(status_code=401, detail="Session expired or invalid")

    try:
        user_id = ObjectId(session["user_id"])
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid session") from exc

    user = await db.users.find_one({"_id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/checkout-session")
async def create_checkout_session(request: Request, payload: CheckoutSessionRequest):
    _get_stripe_client()
    db = request.app.mongodb
    user = await _get_user_from_request(request)

    price_id = payload.price_id or settings.stripe_price_id
    if not price_id:
        raise HTTPException(status_code=400, detail="Missing Stripe price id")

    customer_id = user.get("stripe_customer_id")
    if not customer_id:
        customer = stripe.Customer.create(
            email=user.get("email"),
            name=user.get("full_name"),
            metadata={"user_id": str(user["_id"])},
        )
        customer_id = customer["id"]
        await db.users.update_one(
            {"_id": user["_id"]},
            {"$set": {"stripe_customer_id": customer_id, "updated_at": datetime.utcnow()}},
        )

    subscription_data = {}
    if settings.stripe_trial_days and settings.stripe_trial_days > 0:
        subscription_data["trial_period_days"] = settings.stripe_trial_days

    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=settings.stripe_success_url,
        cancel_url=settings.stripe_cancel_url,
        subscription_data=subscription_data or None,
        client_reference_id=str(user["_id"]),
        metadata={"user_id": str(user["_id"]), "plan": payload.plan or "monthly"},
    )

    return {"url": session.url}


@router.post("/portal-session")
async def create_portal_session(request: Request):
    _get_stripe_client()
    user = await _get_user_from_request(request)

    customer_id = user.get("stripe_customer_id")
    if not customer_id:
        raise HTTPException(status_code=400, detail="Stripe customer not found")

    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=settings.stripe_portal_return_url,
    )
    return {"url": session.url}


@router.post("/cancel")
async def cancel_subscription(request: Request):
    _get_stripe_client()
    db = request.app.mongodb
    user = await _get_user_from_request(request)

    subscription = user.get("subscription") or {}
    subscription_id = subscription.get("id")
    if not subscription_id:
        raise HTTPException(status_code=400, detail="No active subscription to cancel")

    stripe.Subscription.modify(subscription_id, cancel_at_period_end=True)
    await db.users.update_one(
        {"_id": user["_id"]},
        {
            "$set": {
                "subscription.cancel_at_period_end": True,
                "updated_at": datetime.utcnow(),
            }
        },
    )
    return {"status": "ok"}
