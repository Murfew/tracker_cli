import re
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


class ExerciseRow(NamedTuple):
    id: int
    name: str


class SetRow(NamedTuple):
    id: int
    weight: float
    reps: int
    day: date
    exercise_id: int


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
                exercise_id INTEGER NOT NULL REFERENCES exercises(id) ON DELETE CASCADE
                );
            """
        )


def get_exercise(name: str) -> ExerciseRow | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM exercises WHERE name = ?", (name,)).fetchone()
        return ExerciseRow(*row) if row else None


def create_exercise(name: str) -> ExerciseRow:
    with get_connection() as conn:
        row = conn.execute(
            "INSERT INTO exercises (name) VALUES (?) RETURNING id, name", (name,)
        ).fetchone()
        return ExerciseRow(*row)


def create_set(weight: float, reps: int, day: date, exercise_id: int) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO sets (weight, reps, day, exercise_id) VALUES (?, ?, ?, ?)",
            (weight, reps, day, exercise_id),
        )
