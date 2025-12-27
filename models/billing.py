from pydantic import BaseModel
from typing import Optional


class SubscriptionInfo(BaseModel):
    id: Optional[str] = None
    status: Optional[str] = None
    price_id: Optional[str] = None
    current_period_end: Optional[int] = None
    cancel_at_period_end: Optional[bool] = None
    trial_end: Optional[int] = None


class CheckoutSessionRequest(BaseModel):
    price_id: Optional[str] = None
    plan: Optional[str] = None
    payment_method: Optional[str] = None
