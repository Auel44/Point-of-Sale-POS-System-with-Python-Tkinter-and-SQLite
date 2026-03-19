"""Database connection helpers for the POS system."""

from pathlib import Path
import sqlite3


DB_FILE = Path(__file__).resolve().parent.parent / "pos_system.db"


def get_connection() -> sqlite3.Connection:
	"""Return a SQLite connection with foreign keys enabled."""
	connection = sqlite3.connect(DB_FILE)
	connection.execute("PRAGMA foreign_keys = ON;")
	return connection
