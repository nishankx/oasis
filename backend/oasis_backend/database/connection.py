"""
Database connection and lifecycle manager for SQLite.
"""

from __future__ import annotations
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional
from oasis_backend.config import settings


class DatabaseManager:
    def __init__(self, db_path: Optional[str | Path] = None):
        if db_path is None:
            self.db_path = str(settings.resolve_db_path())
        else:
            self.db_path = str(db_path)

    def init_db(self) -> None:
        """Initialize database tables using schema.sql."""
        schema_file = Path(__file__).parent / "schema.sql"
        schema_sql = schema_file.read_text(encoding="utf-8")
        with self.get_connection() as conn:
            conn.executescript(schema_sql)

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager yielding a configured sqlite3 connection with WAL mode and autocommit."""
        conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
        conn.isolation_level = None  # Autocommit mode for concurrent WAL transactions
        conn.row_factory = sqlite3.Row
        try:
            if self.db_path != ":memory:":
                conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA foreign_keys=ON;")
            yield conn
        except Exception:
            raise
        finally:
            conn.close()


# Global database manager instance
db_manager = DatabaseManager()


def get_db() -> Generator[sqlite3.Connection, None, None]:
    """FastAPI dependency for accessing database connection."""
    with db_manager.get_connection() as conn:
        yield conn
