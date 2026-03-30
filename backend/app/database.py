import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .config import settings

_SCHEMA_PATH = Path(__file__).resolve().parent / "db" / "schema.sql"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.database_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def get_db():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Create all tables from schema.sql."""
    schema_sql = _SCHEMA_PATH.read_text(encoding="utf-8")
    with get_db() as conn:
        conn.executescript(schema_sql)
    print(f"Database initialized at {settings.database_path}")
