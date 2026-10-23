import sqlite3
from datetime import datetime
from typing import Annotated

import typer

app = typer.Typer()

DB_FILE = "app.db"


@app.callback()
def init_db() -> None:
    conn = get_db()
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


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


@app.command()
def log(
    name: Annotated[
        str,
        typer.Argument(
            help='Exercise name, e.g. "bench press". Quote names with spaces.'
        ),
    ],
    weight: Annotated[float, typer.Option(help="Weight in lbs.")],
    reps: Annotated[int, typer.Option(help="Number of reps.")],
    day: Annotated[
        datetime,
        typer.Option(
            formats=["%Y-%m-%d"],
            default_factory=datetime.now,
            help="Date the set was done. Defaults to today.",
        ),
    ],
) -> None:
    """
    Record a set for an exercise.
    """


@app.command()
def week() -> None:
    """
    See this week's volume and best set per exercise.

    The week runs Monday to Sunday. Volume is weight x reps,
    summed across all sets of an exercise. Best set is the
    heaviest weight lifted, with ties broken by most reps.
    """


@app.command()
def recent(
    limit: Annotated[int, typer.Option(help="Number of sets to show.")] = 10,
) -> None:
    """
    View the most recent sets, newest first.
    """
