import difflib
from datetime import date, datetime, timedelta
from typing import Annotated, NamedTuple

import typer
from rich import print
from rich.console import Console
from rich.table import Table

from tracker_cli import db

app = typer.Typer()
exercises_app = typer.Typer(help="Manage the exercises you can log sets for.")
app.add_typer(exercises_app, name="exercise")

console = Console()


class CliConfig(NamedTuple):
    db_path: str


def show_table(title: str, data: list[db.Set]) -> None:
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


def _as_cli_config(value: object) -> CliConfig:
    """
    Return the CLI config stored on the Typer context, failing loudly if it's missing.
    """
    if not isinstance(value, CliConfig):
        raise TypeError(f"expected CliConfig, got {type(value).__name__}")
    return value


@app.callback()
def main(
    ctx: typer.Context,
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
    ctx.obj = CliConfig(db_path)

    db.init_db(db_path)


def non_negative_number(value: float) -> float:
    if value < 0:
        raise typer.BadParameter("Value must not be negative.")
    return value


def non_empty_lowercase_string(value: str) -> str:
    if value.strip() == "":
        raise typer.BadParameter("Value must not be empty.")
    return value.lower().strip()


@exercises_app.command()
def add(
    ctx: typer.Context,
    name: Annotated[
        str,
        typer.Argument(
            callback=non_empty_lowercase_string,
            help='Exercise name, e.g. "bench press". Quote names with spaces.',
        ),
    ],
) -> None:
    """
    Register an exercise so you can log sets for it. Names ignore letter case.
    """
    config = _as_cli_config(ctx.obj)

    exercise = db.create_exercise(config.db_path, name)

    if exercise is None:
        print(f"[red]×[/red] {name.title()} is already registered.")  # noqa: RUF001
        raise typer.Exit(1)

    print(f"[green]✓[/green] Added {name.title()}. You can now log sets for it.")


@app.command()
def log(
    ctx: typer.Context,
    name: Annotated[
        str,
        typer.Argument(
            callback=non_empty_lowercase_string,
            help='Exercise name, e.g. "bench press". Quote names with spaces.',
        ),
    ],
    weight: Annotated[
        float, typer.Option(callback=non_negative_number, help="Weight lifted, in lbs.")
    ],
    reps: Annotated[
        int, typer.Option(callback=non_negative_number, help="Number of reps.")
    ],
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
    config = _as_cli_config(ctx.obj)

    exercises = db.get_exercises(config.db_path)
    exercises_by_name = {exercise.name: exercise for exercise in exercises}

    exercise = exercises_by_name.get(name)

    if exercise is None:
        matches = difflib.get_close_matches(
            name, list(exercises_by_name.keys()), n=1, cutoff=0.6
        )

        print("[red]×[/red] Exercise does not exist.")  # noqa: RUF001

        if matches and typer.confirm(f"Did you mean '{matches[0]}'?", default=True):
            exercise = exercises_by_name[matches[0]]
        else:
            raise typer.Exit(1)

    db.create_set(config.db_path, weight, reps, day.date(), exercise.id)

    print(f"[green]✓[/green] Logged {exercise.name.title()}: {weight:g} lbs × {reps}")  # noqa: RUF001


@app.command()
def week(
    ctx: typer.Context,
) -> None:
    """
    Show this week's volume and best set per exercise.

    The week runs Monday to Sunday. Volume is weight x reps,
    summed across all sets. Best set is the
    heaviest weight lifted, with ties broken by most reps.
    """
    config = _as_cli_config(ctx.obj)

    today = date.today()  # noqa: DTZ011
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    sets = db.get_weekly_sets(config.db_path, str(start_of_week), str(end_of_week))

    if not sets:
        print("No sets logged this week yet.")
    else:
        volume = sum(row.weight * row.reps for row in sets)
        print(f"Total volume this week: [bold]{volume:,g}[/bold] lbs")

        best: dict[str, db.Set] = {}
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
    ctx: typer.Context,
    limit: Annotated[int, typer.Option(help="Number of sets to show.")] = 10,
) -> None:
    """
    Show your most recent sets, newest first.
    """
    config = _as_cli_config(ctx.obj)

    sets = db.get_recent_sets(config.db_path, limit)

    if not sets:
        print("No sets logged yet.")
    else:
        show_table(f"Last {len(sets)} set{'s' if len(sets) != 1 else ''}", sets)
