import os
from datetime import datetime
from typing import Annotated

import typer

from tracker_cli.db import init_db

app = typer.Typer()


@app.callback()
def main(
    db_path: Annotated[str, typer.Option("--db", envvar="APP_DB_PATH")] = "app.db",
) -> None:
    os.environ["MYTOOL_DB_PATH"] = db_path
    init_db()


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
