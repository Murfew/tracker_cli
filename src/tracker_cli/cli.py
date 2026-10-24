import os
from datetime import datetime
from typing import Annotated

import typer
from rich import print
from rich.console import Console
from rich.table import Table

from tracker_cli import db

app = typer.Typer()


@app.callback()
def main(
    db_path: Annotated[str, typer.Option("--db", envvar="APP_DB_PATH")] = "app.db",
) -> None:
    os.environ["APP_DB_PATH"] = db_path
    db.init_db()


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
    name = name.lower().strip()
    day_as_date = day.date()

    db.create_set(name, weight, reps, day_as_date)


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
    sets = db.get_sets(limit)

    if not sets:
        print("No sets logged yet.")
    else:
        console = Console()
        table = Table(title=f"Most recent sets (showing {len(sets)})")
        table.add_column("Date", justify="center")
        table.add_column("Exercise", justify="left")
        table.add_column("Weight (lbs)", justify="right")
        table.add_column("Reps", justify="right")

        for row in sets:
            table.add_row(
                str(row.day),
                row.exercise_name.title(),
                f"{row.weight:g}",
                str(row.reps),
            )

        console.print(table)
