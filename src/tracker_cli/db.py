import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from datetime import date
from typing import NamedTuple


@contextmanager
def get_connection(db_path: str) -> Generator[sqlite3.Connection]:
    conn = sqlite3.connect(db_path)

    try:
        with conn:
            conn.execute("PRAGMA foreign_keys = ON;")
            yield conn
    finally:
        conn.close()


class SetRow(NamedTuple):
    exercise_name: str
    weight: float
    reps: int
    day: date


def init_db(db_path: str) -> None:
    with get_connection(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sets (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                weight REAL NOT NULL,
                reps INTEGER NOT NULL,
                day DATE NOT NULL
                );
            """
        )


def create_set(db_path: str, name: str, weight: float, reps: int, day: date) -> None:
    with get_connection(db_path) as conn:
        conn.execute(
            "INSERT INTO sets (name, weight, reps, day) VALUES (?, ?, ?, ?)",
            (name, weight, reps, day.isoformat()),
        )


def get_recent_sets(db_path: str, limit: int) -> list[SetRow]:
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT name, weight, reps, day FROM sets ORDER BY day DESC, id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [_to_set_row(row) for row in rows]


def get_weekly_sets(db_path: str, start: str, end: str) -> list[SetRow]:
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT name, weight, reps, day FROM sets WHERE day BETWEEN ? AND ?",
            (start, end),
        ).fetchall()
        return [_to_set_row(row) for row in rows]


def _to_set_row(row: tuple[str, float, int, str]) -> SetRow:
    name, weight, reps, day = row
    day_as_date = date.fromisoformat(day)
    return SetRow(name, weight, reps, day_as_date)
