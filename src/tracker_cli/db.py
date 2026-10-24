import sqlite3

from tracker_cli.config import get_db_path


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(get_db_path())
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


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
        conn.commit()
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
        conn.commit()
        conn.close()
