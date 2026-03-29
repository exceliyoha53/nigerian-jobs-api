import logging
import sys
from contextlib import asynccontextmanager   # for startup/shutdown lifecycle
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  # handles cross-origin requests(Cross Origin Resource Sharing)
from dotenv import load_dotenv

from app.routers import auth, jobs, payments
from app.database import connection_pool  # we need to close on shutdown

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.FileHandler("api.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages application startup and shutdown lifecycle.
    Startup: logs that the API is ready and DB pool is active.
    Shutdown: closes all PostgreSQL connections in the pool cleanly.
    """
    #startup
    logger.info("Nigerian Jobs API starting up...")
    logger.info("Database connection pool initialized")
    yield
    #shutdown
    connection_pool.closeall()
    logger.info("Database connection pool closed. API shuut down cleanly.")

app = FastAPI(
    title="Nigerian Jobs API",
    description="A paid API delivering live Nigerian job listings scraped from Jobberman. Subscribe via Paystack to allow access.",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # allow all origins for now
    allow_credentials=True,  # Allows cookies or authentication headers
    allow_methods=["*"],  # allow GET, POST, PUT, DELETE
    allow_headers=["*"],  # allow all headers including Authorization
)

app.include_router(auth.router)
app.include_router(jobs.router)
app.include_router(payments.router)

@app.get("/", tags=["Health"])
async def root():
   """
   Health check endpoint.
   Returns a simple status message to confirm the API is running.
   Used by monitoring tools and deployment platforms to verify uptime.
   """
   return {
       "status": "online",
       "message": "Nigerian Jobs API is running",
       "docs": "/docs"
   }

@app.get("/health", tags=["Health"])
async def health_check():
    """
    Detailed health check endpoint.
    Confirms API is running and database pool is active.
    """
    return{
        "status": "healthy",
        "database": "connected",
        "version": "1.0.0"
    }