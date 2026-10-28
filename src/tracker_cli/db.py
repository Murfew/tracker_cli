import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from datetime import date
from typing import NamedTuple


@contextmanager
def get_connection(db_path: str) -> Generator[sqlite3.Connection]:
    """Open a connection with foreign keys enforced, as one transaction.

    The transaction commits if the block finishes and rolls back if it raises.
    The connection is always closed afterwards.

    Args:
        db_path: Path to the SQLite database file.

    Yields:
        An open connection to the database.
    """
    conn = sqlite3.connect(db_path)

    try:
        with conn:
            conn.execute("PRAGMA foreign_keys = ON;")
            yield conn
    finally:
        conn.close()


class ExerciseRow(NamedTuple):
    """One row of the `exercises` table.

    Attributes:
        id: Primary key.
        name: Exercise name, stored in lowercase.
    """

    id: int
    name: str


def _to_exercise_row(row: tuple[int, str]) -> ExerciseRow:
    """Return a raw `(id, name)` row as an `ExerciseRow`."""
    return ExerciseRow(*row)


class LoggedSet(NamedTuple):
    """One logged set, joined with the name of its exercise.

    Attributes:
        exercise_name: Name of the exercise the set was for.
        weight: Weight lifted, in lbs.
        reps: Number of reps.
        day: Date the set was done.
    """

    exercise_name: str
    weight: float
    reps: int
    day: date


def _to_logged_set(row: tuple[str, float, int, str]) -> LoggedSet:
    """Return a raw `(name, weight, reps, day)` row as a `LoggedSet`."""
    name, weight, reps, day = row
    return LoggedSet(name, weight, reps, date.fromisoformat(day))


def init_db(db_path: str) -> None:
    """Create the `exercises` and `sets` tables if they don't exist yet.

    Safe to call on every run: existing tables and data are left alone.

    Args:
        db_path: Path to the SQLite database file. Created if missing.
    """
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
    """Add an exercise.

    Args:
        db_path: Path to the SQLite database file.
        name: Exercise name. Must not have leading or trailing whitespace.

    Returns:
        The new row, or None if an exercise with this name already exists
        (compared case-insensitively).
    """
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
    """Look up one exercise by name, ignoring letter case.

    Args:
        db_path: Path to the SQLite database file.
        name: Exercise name to look for.

    Returns:
        The matching row, or None if there is no exercise with that name.
    """
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT id, name FROM exercises WHERE name = ?", (name,)
        ).fetchone()

        return _to_exercise_row(row) if row else None


def get_exercises(db_path: str) -> list[ExerciseRow]:
    """Return every registered exercise.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        All exercises, in no particular order. Empty if none are registered.
    """
    with get_connection(db_path) as conn:
        rows = conn.execute("SELECT id, name FROM exercises").fetchall()
        return [_to_exercise_row(row) for row in rows]


def create_set(
    db_path: str, weight: float, reps: int, day: date, exercise_id: int
) -> None:
    """Save one set.

    Args:
        db_path: Path to the SQLite database file.
        weight: Weight lifted, in lbs. Must not be negative.
        reps: Number of reps. Must not be negative.
        day: Date the set was done.
        exercise_id: ID of an existing exercise.
    """
    with get_connection(db_path) as conn:
        conn.execute(
            "INSERT INTO sets (weight, reps, day, exercise_id) VALUES (?, ?, ?, ?)",
            (weight, reps, day.isoformat(), exercise_id),
        )


def get_recent_sets(db_path: str, limit: int) -> list[LoggedSet]:
    """Return the most recently done sets.

    Args:
        db_path: Path to the SQLite database file.
        limit: Maximum number of sets to return.

    Returns:
        Sets ordered newest first by date. Sets on the same day are ordered by
        most recently logged.
    """
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT name, weight, reps, day FROM sets JOIN exercises ON sets.exercise_id = exercises.id
            ORDER BY day DESC, sets.id DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [_to_logged_set(row) for row in rows]


def get_sets_in_date_range(db_path: str, start: str, end: str) -> list[LoggedSet]:
    """Return every set done between two dates, inclusive.

    Args:
        db_path: Path to the SQLite database file.
        start: First day of the range, as an ISO date (YYYY-MM-DD).
        end: Last day of the range, as an ISO date (YYYY-MM-DD).

    Returns:
        Sets in the range, in no particular order.
    """
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT name, weight, reps, day FROM sets JOIN exercises ON sets.exercise_id = exercises.id
            WHERE day BETWEEN ? AND ?
            """,
            (start, end),
        ).fetchall()
        return [_to_logged_set(row) for row in rows]
