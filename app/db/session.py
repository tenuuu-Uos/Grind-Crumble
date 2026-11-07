import sqlite3
from typing import Generator
from app.config import DB_PATH

def get_db_connection() -> sqlite3.Connection:
    """Creates a new SQLite connection with foreign keys and dict-like row factory."""
    conn = sqlite3.connect(DB_PATH, timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def get_db() -> Generator[sqlite3.Connection, None, None]:
    """FastAPI dependency for database connection."""
    conn = get_db_connection()
    try:
        yield conn
    finally:
        conn.close()
