import logging
import os
import httpx
from fastapi import APIRouter, HTTPException, status, Depends, Query
from app.models.schemas import PaymentInitResponse, PaymentVerifyResponse
from app.auth import get_current_user
from app.database import get_connection, return_connection, get_db_cursor
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payments", tags=["Payments"])

PAYSTACK_SECRET_KEY =  os.getenv("PAYSTACK_SECRET_KEY")
PAYSTACK_INITIALIZE_URL = "https://api.paystack.co/transaction/initialize"
PAYSTACK_VERIFY_URL = "https://api.paystack.co/transaction/verify"
SUBSCRIPTION_AMOUNT_KOBO = 500000 # 100 kobo = 1 naira

@router.post("/subscribe", response_model=PaymentInitResponse)
async def subscribe(current_user: dict = Depends(get_current_user)) -> PaymentInitResponse:
    """
    Initializes a paystack payment for the authenticated user.
    Calls Paystack's initialize endpoint to generate a checkout URL.
    The user must visit the returned URL to complete payment.
    After payment, call GET /payments/verify to unlock API access.
    
    Parameters:
        current_user (dict): Injected by Depends(get_current_user) - contains email
    
    Returns:
        HTTPException 400: If user is already subscribed
        HTTPException 502: If Paystack API call fails
    """
    conn = get_connection()
    cursor = get_db_cursor(conn)

    try:
        cursor.execute(
            "SELECT is_subscribed FROM users WHERE email = %s",
            (current_user["email"],)
        )
        user = cursor.fetchone()
        if user and user["is_subscribed"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You already have an active subscription"
            )
        
        # httpx.AsyncClient is the async version of requests.get()
        async with httpx.AsyncClient() as client:
            response = await client.post(
                PAYSTACK_INITIALIZE_URL,
                json={
                    "email": current_user["email"],
                    "amount": SUBSCRIPTION_AMOUNT_KOBO,
                    "currency": "NGN",
                    "metadata": {
                        "user_email": current_user["email"]  # extra data stored with the transaction
                    }
                },
                headers={
                    "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
                    "Content-Type": "application/json"
                },
                timeout=30.0
            )
        paystack_data = response.json()
        
        if not paystack_data.get("status"):
        # Paystack returns {"status": false} when something goes wrong
            logger.error(f"Paystack init failed: {paystack_data}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Payment initialization failed. Try again later."
            )
        logger.info(f"Payment initialized for {current_user["email"]}")
        
        return {
            "authorization_url": paystack_data["data"]["authorization_url"],
            "reference": paystack_data["data"]["reference"]
        }
        
    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Payment init error for {current_user['email']}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Payment initialization failed"
        )
    
    finally:
        cursor.close()
        return_connection(conn)


@router.get("/verify", response_model=PaymentVerifyResponse)
async def verify_payment(
    reference: str = Query(description="Transaction reference from /payments/subscribe"),
    current_user: dict = Depends(get_current_user)
) -> PaymentVerifyResponse:
    """
    Verifies a Paystack payment and unlocks API access if successful.
    Call this after the user completes payment on the Paystack checkout page.
    Updates is_subscribed to True in the database on successful payment.

    Parameters:
        reference (str): The transaction reference from the subscribe endpoint
        current_user (dict): Injected by Depends(get_current_user)

    Returns:
        PaymentVerifyResponse: Payment status and updated subscription state

    Raises:
        HTTPException 400: If payment is not successful
        HTTPException 502: If Paystacj verification fails
    """

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{PAYSTACK_VERIFY_URL}/{reference}",
                headers={
                    "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"
                },
                timeout = 30.0
            )
        paystack_data = response.json()

        if not paystack_data.get("status"):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not verify payment with Paystack"
            )
        payment_status = paystack_data["data"]["status"]  # "success", "failed", "pending"

        if payment_status != "success":
            logger.warning(f"Payment not successful for {current_user['email']}: {payment_status}")
            return {
                "status": payment_status,
                "message": f"Payment status {payment_status}. Access not unlocked.",
                "is_subscribed": False
            }

        conn = get_connection()
        cursor = get_db_cursor(conn)

        try:
            cursor.execute(
                "UPDATE users SET is_subscribed = TRUE WHERE email = %s",
                (current_user['email'],)
            )
            conn.commit()
            logger.info(f"Subscription activated for {current_user['email']}")

        finally:
            cursor.close()
            return_connection(conn)
        
        return {
            "status": "success",
            "message": "Payment verified. Your API access is now active.",
            "is_subscribed": True
        }

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Payment verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Payment verification failed"
        )