import sqlite3
from collections.abc import Generator
from contextlib import contextmanager

from tracker_cli.config import get_db_path


@contextmanager
def get_connection() -> Generator[sqlite3.Connection]:
    conn = sqlite3.connect(get_db_path())

    try:
        with conn:
            conn.execute("PRAGMA foreign_keys = ON;")
            yield conn
    finally:
        conn.close()


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS exercises (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE
                );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sets (
                id INTEGER PRIMARY KEY,
                weight REAL NOT NULL,
                reps INTEGER NOT NULL,
                day DATE NOT NULL,
                exercise_id INTEGER NOT NULL REFERENCES exercises(id)
                );
            """
        )
