from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


# --- AUTH SCHEMAS ---------------------------------------
class UserRegister(BaseModel):
    """
    Request schema for POST /auth/register.
    Validates that the email is a real email format and password is provided.
    """
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    """
    Request schema for POST /auth/login.
    Same fields as register - email and password to verify identity.
    """
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    """
    Response schema for successful login.
    Returns the JWT token and its type.
    The token type is always 'bearer' (HTTP auth standard)
    """
    access_token: str
    token_type: str

class UserResponse(BaseModel):
    """
    Response schema for returning data.
    Deliberately excludes password_hash
    
    Parameters:
    id (int): The user's database ID
    email (str): The user's email address
    is_subscribed (bool): Whether the user has an active Paystack susbsciption
    created_at (datetime): When the account was created
    """
    id: int
    email: str
    is_subscribed: bool
    created_at: datetime

#--- JOB SCHEMAS----------------------------------------------
class JobResponse(BaseModel):
    """
    Response schema for a single job listing.
    Maps directly to the jobs table from month 1.
    Optional fields handle cases where salary or location  wasn't scraped.
    
    Parameters:
        id (int): Database row ID
        title (str): Job title
        company (str): Company name
        location (Optional[str]): Job location - None if not listed
        salary (Optional[str]): salary range - None if not listed
        job_url (str): Direct link to the job posting
        scraped_at (datetime): When the job was added to the vault
    """
    id: int
    title: str
    company: str
    location: Optional[str] = None
    salary: Optional[str] = None
    job_url: str
    scraped_at: datetime

class JobsListResponse(BaseModel):
    """
    Response schema for paginated job listings.
    Wraps a list of jos with metadata about the total available.
    
    Parameters:
        jobs (list[JobResponse]): The list of job objects for this page
        total (int): Total jobs in the vault matching the query
        page (int): Current page number
        per_page (int): How many jobs per page
    """
    jobs: list[JobResponse]
    total: int             
    page: int              
    per_page: int

# --- PAYMENT SCHEMAS ---------------------------------------------
class PaymentInitResponse(BaseModel):
    """
    Response schema for POST /payments/subscribe.
    Returns the Paystack checkout URL the user must visit to complete payment.

    Parameters:
        authorization_url (str): The Paystack hosted payment page URL
        reference (str): Unique transaction reference for verification later
    """
    authorization_url: str  # redirect user here to complete payment on paystack
    reference: str          # used in /payments/verify to confirm payment

class PaymentVerifyResponse(BaseModel):
    """
    Response schema for GET /payments/verify.
    Returns whether the payment succeeded and the updated subscription status.

    Parameters:
        status (str): 'success' or 'failed'
        message (str): Human readable result
        is_subscribed (bool): Updated subscription status after verification
    """
    status: str
    message: str
    is_subscribed: bool