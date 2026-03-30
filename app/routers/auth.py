import logging
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm
from app.models.schemas import UserRegister, UserLogin, TokenResponse, UserResponse
from app.auth import hash_password, verify_password, create_access_token, get_current_user
from app.database import get_connection, return_connection, get_db_cursor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user: UserRegister) -> UserResponse:
    """
    Registers a new user account.
    Hashes the password before storing — raw passwords never touch the database.
    Returns the created user without the password hash.

    Parameters:
        user (UserRegister): Request body with email and password

    Returns:
        UserResponse: The created user's data excluding password

    Raises:
        HTTPException 400: If the email is already registered
    """
    conn = get_connection()
    cursor = get_db_cursor(conn)
    try:
        cursor.execute("SELECT id FROM users WHERE email = %s", (user.email,))  # tuple with one iten
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        hashed = hash_password(user.password)

        cursor.execute("""
                       INSERT INTO users (email, password_hash, is_subscribed)
                       VALUES (%s, %s, %s)
                       RETURNING id, email, is_subscribed, created_at
                       """, (user.email, hashed, False))
        conn.commit()
        new_user = dict(cursor.fetchone())  # convert RealDictRow to plain dict
        logger.info(f"New user registered: {user.email}")
        return new_user
    except HTTPException:
        raise  #raise HTTP excepetion as-is
    
    except Exception as e:
        conn.rollback()  # undo any partial changes if something went wrong
        logger.error(f"Registration error for {user.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )
    
    finally:
        cursor.close()
        return_connection(conn)


@router.post("/login", response_model=TokenResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends()) -> TokenResponse:
    """
    Authenticates a user and returns a JWT access token.
    The token must be included in the Authorization header for protected endpoints.
    Header format: Authorization: Bearer <token>

    Parameters:
        user (UserLogin): Request body with email and password

    Returns:
        TokenResponse: JWT access token and token type

    Raises:
        HTTPException 401: If email not found or password is incorrect
    """
    user_email = form_data.username 
    user_password = form_data.password
    conn = get_connection()
    cursor = get_db_cursor(conn)

    try:
        cursor.execute(
            "SELECT id, email, password_hash, is_subscribed FROM users WHERE email = %s",
            (user_email,)
        )   
        db_user = cursor.fetchone()
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        if not verify_password(user_password, db_user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # password matched — create token with email as the subject
        token = create_access_token(data={"sub": user_email})
        logger.info(f"User logged in: {user_email}")

        return {"access_token": token, "token_type": "bearer"}
     
    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Login error for {user_email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login Failed"
        )
    finally:
        cursor.close()
        return_connection(conn)

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)) -> UserResponse:
    """
    Returns the currently authenticated user's profile.
    Protected endpoint — requires a valid JWT token in the Authorization header.
    Used to verify a token is still valid and fetch fresh user data.
    Parameters:
        current_user (dict): Injected by Depends(get_current_user) — contains email
    Returns:
        UserResponse: The authenticated user's data excluding password
    """
    conn = get_connection()
    cursor = get_db_cursor(conn)

    try:
        cursor.execute(
            "SELECT id, email, is_subscribed, created_at FROM users WHERE email = %s",
            (current_user["email"],)
        )
        user = cursor.fetchone()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return dict(user)
    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error fetching user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not fetch user profile"
        )
    finally:
        cursor.close()
        return_connection(conn)
