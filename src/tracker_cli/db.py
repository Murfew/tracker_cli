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


class ExerciseRow(NamedTuple):
    id: int
    name: str


def _to_exercise_row(row: tuple[int, str]) -> ExerciseRow:
    return ExerciseRow(*row)


class Set(NamedTuple):
    exercise_name: str
    weight: float
    reps: int
    day: date


def _to_set(row: tuple[str, float, int, str]) -> Set:
    name, weight, reps, day = row
    return Set(name, weight, reps, date.fromisoformat(day))


def init_db(db_path: str) -> None:
    with get_connection(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS exercises (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT NOT NULL UNIQUE COLLATE NOCASE CHECK (name == TRIM(name))
            );
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sets (
                id INTEGER PRIMARY KEY,
                weight REAL NOT NULL CHECK(weight >= 0),
                reps INTEGER NOT NULL CHECK(reps >= 0),
                day DATE NOT NULL,
                exercise_id INTEGER NOT NULL REFERENCES exercises(id)
                );
            """
        )


def create_exercise(db_path: str, name: str) -> ExerciseRow | None:
    with get_connection(db_path) as conn:
        try:
            cur = conn.execute(
                "INSERT INTO exercises (name) VALUES (?) RETURNING id, name", (name,)
            )
        except sqlite3.IntegrityError:
            return None
        else:
            return _to_exercise_row(cur.fetchone())


def get_exercise_by_name(db_path: str, name: str) -> ExerciseRow | None:
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT id, name FROM exercises WHERE name = ?", (name,)
        ).fetchone()

        return _to_exercise_row(row) if row else None


def get_exercises(db_path: str) -> list[ExerciseRow]:
    with get_connection(db_path) as conn:
        rows = conn.execute("SELECT id, name FROM exercises").fetchall()
        return [_to_exercise_row(row) for row in rows]


def create_set(
    db_path: str, weight: float, reps: int, day: date, exercise_id: int
) -> None:
    with get_connection(db_path) as conn:
        conn.execute(
            "INSERT INTO sets (weight, reps, day, exercise_id) VALUES (?, ?, ?, ?)",
            (weight, reps, day.isoformat(), exercise_id),
        )


def get_recent_sets(db_path: str, limit: int) -> list[Set]:
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT name, weight, reps, day FROM sets JOIN exercises ON sets.exercise_id = exercises.id
            ORDER BY day DESC, sets.id DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [_to_set(row) for row in rows]


def get_weekly_sets(db_path: str, start: str, end: str) -> list[Set]:
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT name, weight, reps, day FROM sets JOIN exercises ON sets.exercise_id = exercises.id
            WHERE day BETWEEN ? AND ?
            """,
            (start, end),
        ).fetchall()
        return [_to_set(row) for row in rows]
