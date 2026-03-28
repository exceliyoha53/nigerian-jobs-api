import logging
from fastapi import APIRouter, HTTPException, status, Depends, Query  # Query handles URL params
from app.models.schemas import JobsListResponse
from app.auth import get_current_user
from app.database import get_connection, return_connection, get_db_cursor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])

def check_subscription(conn, email: str) -> None:
    """
    Verifies that the authenticated user has an active subscription.
    Raises HTTP 403 if the user exists but is not subscribed.
    Called at the start of every paid endpoint.
    
    Parameters:
        conn: active psycopg2 connection from the pool
        email (str): the authenticated user's emaill from the JWT token
        
    Raises:
        HTTPException 403: If the user is not subscribed
        HTTPException 404: If the user is not found in the database
        """
    cursor = get_db_cursor(conn)
    cursor.execute(
        "SELECT is_subscribed FROM users WHERE email = %s", (email,)
    )
    user = cursor.fetchone()
    cursor.close()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    if not user["is_subscribed"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Active subscription required. Visit /payments/subscribe to unlock access."
        )

@router.get("/", response_model=JobsListResponse)
async def get_jobs(
    page: int = Query(default=1, ge=1, description="Page number, starts at 1"),
    per_page: int = Query(default=10, ge=1, le=50, description="Jobs per page, max 50"),
    location: str = Query(default=None, description="Filter by location keyword e.g Lagos,"),
    current_user: dict = Depends(get_current_user)
) -> JobsListResponse:
    """
    Returns paginated job listings from the Nigerian jobs vault.
    Protected endpoint — requires a valid JWT token and active subscription.
    Supports optional location filtering.

    Parameters:
        page (int): Page number starting at 1. Default 1.
        per_page (int): Jobs per page, max 50. Default 10.
        location (str): Optional location filter — case-insensitive contains search
        current_user (dict): Injected by Depends(get_current_user)

    Returns:
        JobsListResponse: Paginated list of jobs with total count and pagination metadata

    Raises:
        HTTPException 401: If token is missing or invalid
        HTTPException 403: If user is not subscribed
    """
    conn = get_connection()
    cursor = get_db_cursor(conn)

    try:
        check_subscription(conn, current_user["email"])

        offset = (page - 1) * per_page  # calculates how many rows to skip

        if location:
          # filter query, count and fetch only matching location
          cursor.execute(
              "SELECT COUNT(*) AS total FROM jobs WHERE LOWER(location) LIKE LOWER(%s)",
              (f"%{location}%",)
          )
          total = cursor.fetchone()["total"]
          cursor.execute("""
                         SELECT id, title, company, location, salary, job_url, scraped_at
                         FROM jobs
                         WHERE LOWER(location) LIKE LOWER(%s)
                         ORDER BY scraped_at DESC
                         LIMIT %s OFFSET %s
                    """, (f"%{location}%", per_page, offset))
        else:
            # unfiltered query - All jobs paginated
            cursor.execute("SELECT COUNT(*) AS total FROM jobs")
            total = cursor.fetchone()["total"]

            cursor.execute("""
                        SELECT id, title, company, location, salary, job_url, scraped_at
                        FROM jobs
                        ORDER BY scraped_at DESC
                        LIMIT %s OFFSET %s
                    """, (per_page, offset))
        jobs = [dict(row) for row in cursor.fetchall()]  # convert all rows to plain dict
        logger.info(f"User {current_user['email']} fetched page {page} - {len(jobs)} jobs returned")

        return {
            "jobs": jobs,
            "total": total,
            "page": page,
            "per_page": per_page
        }
    
    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error fetching jobs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not fetch jobs"
        )
    
    finally:
        cursor.close()
        return_connection(conn)
