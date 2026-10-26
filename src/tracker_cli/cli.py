import os
from datetime import date, datetime, timedelta
from typing import Annotated

import typer
from rich import print
from rich.console import Console
from rich.table import Table

from tracker_cli import db

app = typer.Typer()
console = Console()


@app.callback()
def main(
    db_path: Annotated[
        str,
        typer.Option(
            "--db",
            envvar="APP_DB_PATH",
            help="Path to the SQLite database file. Put it before the command.",
        ),
    ] = "app.db",
) -> None:
    """
    Track your lifts from the terminal.
    """

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
    weight: Annotated[float, typer.Option(help="Weight lifted, in lbs.")],
    reps: Annotated[int, typer.Option(help="Number of reps.")],
    day: Annotated[
        datetime,
        typer.Option(
            formats=["%Y-%m-%d"],
            default_factory=datetime.now,
            help="Date the set was done. Defaults to today.",
            show_default=False,
        ),
    ],
) -> None:
    """
    Log one set: exercise, weight and reps.
    """
    name = name.lower().strip()
    day_as_date = day.date()

    db.create_set(name, weight, reps, day_as_date)

    print(f"[green]✓[/green] Logged {name.title()}: {weight:g} lbs × {reps}")  # noqa: RUF001


def show_table(title: str, data: list[db.SetRow]) -> None:
    """
    Print sets as a table with exercise, weight, reps and date columns.
    """

    table = Table(title=title)
    table.add_column("Exercise", justify="left", style="cyan")
    table.add_column("Weight (lbs)", justify="right")
    table.add_column("Reps", justify="right")
    table.add_column("Date", justify="center")

    for row in data:
        table.add_row(
            row.exercise_name.title(),
            f"{row.weight:g}",
            str(row.reps),
            f"{row.day.strftime('%a %b %-d')}",
        )

    console.print(table)


@app.command()
def week() -> None:
    """
    Show this week's volume and best set per exercise.

    The week runs Monday to Sunday. Volume is weight x reps,
    summed across all sets. Best set is the
    heaviest weight lifted, with ties broken by most reps.
    """
    today = date.today()  # noqa: DTZ011
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    sets = db.get_weekly_sets(str(start_of_week), str(end_of_week))

    if not sets:
        print("No sets logged this week yet.")
    else:
        volume = sum(row.weight * row.reps for row in sets)
        print(f"Total volume this week: [bold]{volume:,g}[/bold] lbs")

        best: dict[str, db.SetRow] = {}
        for row in sets:
            if row.exercise_name not in best:
                best[row.exercise_name] = row
            else:
                current_best = best[row.exercise_name]
                if (
                    current_best.weight == row.weight and current_best.reps < row.reps
                ) or (current_best.weight < row.weight):
                    best[row.exercise_name] = row
                else:
                    continue

        show_table(
            f"Best sets · {start_of_week.strftime('%b %-d')} – {end_of_week.strftime('%b %-d')}",  # noqa: RUF001
            list(best.values()),
        )


@app.command()
def recent(
    limit: Annotated[int, typer.Option(help="Number of sets to show.")] = 10,
) -> None:
    """
    Show your most recent sets, newest first.
    """
    sets = db.get_recent_sets(limit)

    if not sets:
        print("No sets logged yet.")
    else:
        show_table(f"Last {len(sets)} set{'s' if len(sets) != 1 else ''}", sets)
