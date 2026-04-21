import logging
import os
import sys
from contextlib import asynccontextmanager  # for startup/shutdown lifecycle
from fastapi import FastAPI, Request
from fastapi.middleware.cors import (
    CORSMiddleware,
)  # handles cross-origin requests(Cross Origin Resource Sharing)
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

from app.routers import auth, jobs, payments
from app.database import connection_pool  # we need to close on shutdown
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.limiter import limiter

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[logging.FileHandler("api.log"), logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)

templates = Jinja2Templates(directory="app/templates")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages application startup and shutdown lifecycle.
    Startup: logs that the API is ready and DB pool is active.
    Shutdown: closes all PostgreSQL connections in the pool cleanly.
    """
    # startup
    logger.info("Nigerian Jobs API starting up...")
    required_env_vars = ["SECRET_KEY", "DATABASE_URL", "ALGORITHM"]
    missing = [v for v in required_env_vars if not os.getenv(v)]
    if missing:
        raise RuntimeError(
            f"CRITICAL: Missing required environment variables: {missing}"
        )
    logger.info("Database connection pool initialized")
    yield
    # shutdown
    connection_pool.closeall()
    logger.info("Database connection pool closed. API shuut down cleanly.")


app = FastAPI(
    title="Nigerian Jobs API",
    description="A paid API delivering live Nigerian job listings scraped from Jobberman. Subscribe via Paystack to allow access.",
    version="1.0.0",
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow all origins for now
    allow_credentials=True,  # Allows cookies or authentication headers
    allow_methods=["*"],  # allow GET, POST, PUT, DELETE
    allow_headers=["*"],  # allow all headers including Authorization
)

app.include_router(auth.router)
app.include_router(jobs.router)
app.include_router(payments.router)


@app.get("/", include_in_schema=False)
async def landing(request: Request):
    return templates.TemplateResponse(request=request, name="landing.html")


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Detailed health check endpoint.
    Confirms API is running and database pool is active.
    """
    return {"status": "healthy", "database": "connected", "version": "1.0.0"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Our team has been notified."},
    )
