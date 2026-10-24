import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from datetime import date
from typing import NamedTuple

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


class SetRow(NamedTuple):
    id: int
    exercise_name: str
    weight: float
    reps: int
    day: date


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sets (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                weight REAL NOT NULL,
                reps INTEGER NOT NULL,
                day DATE NOT NULL
                );
            """
        )


def create_set(name: str, weight: float, reps: int, day: date) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO sets (name, weight, reps, day) VALUES (?, ?, ?, ?)",
            (name, weight, reps, day),
        )


def get_sets(limit: int) -> list[SetRow]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM sets ORDER BY day DESC LIMIT ?", (limit,)
        ).fetchall()
        return [SetRow(*row) for row in rows]
