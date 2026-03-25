import psycopg2
import psycopg2.extras  # RealDictCursor for dict row returns
import psycopg2.pool  # Connection pooling
import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

connection_pool = psycopg2.pool.SimpleConnectionPool(
    minconn=1,
    maxconn=10,
    dsn=os.getenv("DATABASE_URL")  # data source name
)

def get_connection() -> psycopg2.extensions.connection:
    """
    Borrows a connection from the pool.
    Must be returned after use with return_connection().
    
    Returns:
        psycopg2 connection object from the pool
    """
    return connection_pool.getconn()

def return_connection(conn: psycopg2.extensions.connection) -> None:
    """
    Returns a borrowed pool connection back to the pool so it can be reused.
    Always called after get_connection() - even if an error occured.
    
    Parameters:
        conn: the connection object to return
    """
    connection_pool.putconn(conn)

def get_db_cursor(conn: psycopg2.extensions.connection):
    """
    Creates a RealDictCursor from a connection.
    RealDictCursor returns rows as dicts instead of tuples.
    
    Parameters:
        conn: an active psycopg2 connection
    Returns:
        psycopg2 RealDictCursor object
    """
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
