import os
import logging
from datetime import datetime, timedelta, timezone  # for token expiry calculation
from typing import Optional

from jose import JWTError, jwt  # creates and verifies JWT tokens
from passlib.context import CryptContext  # handles password hashing
from fastapi import Depends, HTTPException, status  # FastAPI auth utilities
from fastapi.security import OAuth2PasswordBearer  # extracts token from request header
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

SECRET_KEY = os.getenv("SECRET_KEY")   # secret used to sign token
ALGORITHM = os.getenv("ALGORITHM", "HS256")  # signing algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")  # use bcrypt for hashing

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def hash_password(password: str) -> str:
    """
    Hashes a plain text password using bcrypt.
    The result is a one-way hash — the original password cannot be recovered.

    Parameters:
        password (str): The raw password from the registration request

    Returns:
        str: The bcrypt hash to store in the database
    """
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain text password against a stored bcrypt hash.
    Used during login to check if the provided password is correct.

    Parameters:
        plain_password (str): The raw password from the login request
        hashed_password (str): The bcrypt hash stored in the database

    Returns:
        bool: True if the password matches, False if it doesn't
    """
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Creates a signed JWT access token containing the provided data.
    The token expires after ACCESS_TOKEN_EXPIRE_MINUTES unless overridden.

    Parameters:
        data (dict): The payload to encode — typically {"sub": user_email}
        expires_delta (Optional[timedelta]): Custom expiry duration

    Returns:
        str: A signed JWT token string to send to the client
    """
    to_encode = data.copy() # mutating the copy

    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=int(ACCESS_TOKEN_EXPIRE_MINUTES))) # expiry time
    to_encode.update({"exp": expire})  # add expiry to payload

    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM) # sign the token
    logger.info(f"Access token created for: {data.get('sub')}")
    return token

def decode_access_token(token: str) -> Optional[dict]:
    """
    Decodes and verifies a JWT token.
    Returns the payload if valid, None if the token is expired or tampered with.

    Parameters:
        token (str): The JWT string from the request header

    Returns:
        Optional[dict]: The decoded payload, or None if invalid
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        logger.warning(f"Invalid token: {e}")
        return None

async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    FastAPI dependency that extracts and validates the current user from the JWT token
    Inject this into any protected endpoint with: current_user = Depends(get_current_user)

    Parameters:
        token (str): Automatically extracted from the Authorization header by oauth2_scheme
        
    Returns:
        dict: The decoded token payload containing the user's email
        
    Raises:
        HTTPException 401: If the token is missing, expired, or invalid
    """
    # define the error if anything goes wrong
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},  # tells the client how to authenticate
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    
    email:str = payload.get("sub")
    if email is None:
        raise credentials_exception
    return {"email": email}
