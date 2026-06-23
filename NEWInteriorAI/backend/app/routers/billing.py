"""
Billing Router
Stripe subscription checkout and webhook handler.
"""
import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..db import get_db
from ..models.models import User
from ..routers.auth import get_current_user
from ..config import settings

router = APIRouter()
stripe.api_key = settings.stripe_secret_key

PRICE_IDS = {
    "pro":     "price_pro_monthly",      # replace with real Stripe price IDs
    "premium": "price_premium_monthly",
}


class CheckoutRequest(BaseModel):
    plan: str     # pro | premium
    success_url: str = "https://yourdomain.com/dashboard?upgraded=true"
    cancel_url: str  = "https://yourdomain.com/pricing"


@router.post("/create-checkout")
def create_checkout(
    body: CheckoutRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if body.plan not in PRICE_IDS:
        raise HTTPException(status_code=400, detail="Invalid plan")

    session = stripe.checkout.Session.create(
        customer_email=user.email,
        payment_method_types=["card"],
        line_items=[{"price": PRICE_IDS[body.plan], "quantity": 1}],
        mode="subscription",
        success_url=body.success_url,
        cancel_url=body.cancel_url,
        metadata={"user_id": str(user.id), "plan": body.plan},
    )
    return {"checkout_url": session.url}


@router.post("/portal")
def customer_portal(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Redirect to Stripe customer portal to manage subscription."""
    if not user.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No billing account found")

    session = stripe.billing_portal.Session.create(
        customer=user.stripe_customer_id,
        return_url="https://yourdomain.com/dashboard",
    )
    return {"portal_url": session.url}


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Stripe webhook handler.
    Listens for subscription events and updates user plan in DB.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid Stripe signature")

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        user_id = data["metadata"].get("user_id")
        plan = data["metadata"].get("plan")
        customer_id = data.get("customer")
        subscription_id = data.get("subscription")

        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.plan = plan
            user.stripe_customer_id = customer_id
            user.stripe_subscription_id = subscription_id
            db.commit()

    elif event_type in ("customer.subscription.deleted", "customer.subscription.paused"):
        subscription_id = data["id"]
        user = db.query(User).filter(
            User.stripe_subscription_id == subscription_id
        ).first()
        if user:
            user.plan = "free"
            db.commit()

    elif event_type == "customer.subscription.updated":
        subscription_id = data["id"]
        status = data.get("status")
        user = db.query(User).filter(
            User.stripe_subscription_id == subscription_id
        ).first()
        if user and status == "active":
            # Re-confirm plan from metadata if available
            pass

    return {"received": True}
