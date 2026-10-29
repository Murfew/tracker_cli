import math
from datetime import date, datetime
from typing import Annotated, NamedTuple

import typer
from rich import print as rich_print
from rich.console import Console
from rich.table import Table

from tracker_cli import db
from tracker_cli.stats import (
    get_best_sets,
    get_closest_match,
    get_volume,
    get_week_range,
)

app = typer.Typer()
exercises_app = typer.Typer(help="Manage the exercises you can log sets for.")
app.add_typer(exercises_app, name="exercise")

console = Console()


class CliConfig(NamedTuple):
    """Settings shared by every command, stored on the Typer context.

    Attributes:
        db_path: Path to the SQLite database file.
    """

    db_path: str


def _as_cli_config(value: object) -> CliConfig:
    """Return the CLI config stored on the Typer context.

    Args:
        value: The context object, normally `ctx.obj`.

    Returns:
        The same object, typed as a `CliConfig`.

    Raises:
        TypeError: If `value` is not a `CliConfig`, which means the `main`
            callback did not run before the command.
    """
    if not isinstance(value, CliConfig):
        raise TypeError(f"expected CliConfig, got {type(value).__name__}")
    return value


def show_table(title: str, sets: list[db.LoggedSet]) -> None:
    """Print sets as a table with exercise, weight, reps and date columns.

    Args:
        title: Heading shown above the table.
        sets: Sets to show, one per row, in the order given.
    """
    table = Table(title=title)
    table.add_column("Exercise", justify="left", style="cyan")
    table.add_column("Weight (lbs)", justify="right")
    table.add_column("Reps", justify="right")
    table.add_column("Date", justify="center")

    for logged_set in sets:
        table.add_row(
            logged_set.exercise_name.title(),
            f"{logged_set.weight:g}",
            str(logged_set.reps),
            f"{logged_set.day.strftime('%a %b %-d')}",
        )

    console.print(table)


def get_today() -> date:
    """Return today's date in the computer's local time zone.

    This is its own function so tests can replace it with a fixed date
    and not depend on the real clock.

    Returns:
        Today's date, with no time part.
    """
    return date.today()  # ruff: ignore[call-date-today]


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
    """Track your lifts from the terminal."""
    ctx.obj = CliConfig(db_path)

    db.init_db(db_path)


def non_negative_number(value: float) -> float:
    """Reject negative or non-finite numbers.

    Used as a Typer callback for weight and reps.

    Args:
        value: The number the user typed.

    Returns:
        The value, unchanged.

    Raises:
        typer.BadParameter: If value is negative, infinite, or NaN.
    """
    if not math.isfinite(value) or value < 0:
        raise typer.BadParameter("Value must be a finite number, zero or greater.")
    return value


def non_empty_lowercase_string(value: str) -> str:
    """Reject blank text and normalise the rest. Used as a Typer callback for names.

    Args:
        value: The text the user typed.

    Returns:
        The value in lowercase, with leading and trailing whitespace removed.

    Raises:
        typer.BadParameter: If `value` is empty or only whitespace.
    """
    if not value.strip():
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
    """Register an exercise so you can log sets for it. Names ignore letter case."""  # ruff: ignore[docstring-missing-exception]
    config = _as_cli_config(ctx.obj)

    exercise = db.create_exercise(config.db_path, name)

    if exercise is None:
        rich_print(f"[red]×[/red] {name.title()} is already registered.")  # ruff: ignore[ambiguous-unicode-character-string]
        raise typer.Exit(1)

    rich_print(f"[green]✓[/green] Added {name.title()}. You can now log sets for it.")


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
        datetime | None,
        typer.Option(
            formats=["%Y-%m-%d"],
            help="Date the set was done. Defaults to today.",
        ),
    ] = None,
) -> None:
    """Log one set: exercise, weight and reps.

    If the name isn't registered, suggests the closest match and asks you to
    confirm it.
    """  # ruff: ignore[docstring-missing-exception]
    config = _as_cli_config(ctx.obj)
    exercises = db.get_exercises(config.db_path)
    exercises_by_name = {exercise.name: exercise for exercise in exercises}
    exercise_names = list(exercises_by_name.keys())

    name_match = get_closest_match(name, exercise_names)

    # get_closest_match returns the name itself for an exact match, a different
    # registered name for a close match, or None when nothing is close.
    # Only an exact match, or a close match the user confirms, gets logged.
    if name_match != name:
        rich_print("[red]×[/red] Exercise does not exist.")  # ruff: ignore[ambiguous-unicode-character-string]

    if name_match is None:
        raise typer.Exit(1)

    if name_match == name or typer.confirm(
        f"Did you mean '{name_match}'?", default=True
    ):
        exercise = exercises_by_name[name_match]
    else:
        raise typer.Exit(1)

    day_as_date = get_today() if day is None else day.date()

    db.create_set(config.db_path, weight, reps, day_as_date, exercise.id)

    rich_print(
        f"[green]✓[/green] Logged {exercise.name.title()}: {weight:g} lbs × {reps}"  # ruff: ignore[ambiguous-unicode-character-string]
    )


@app.command()
def week(
    ctx: typer.Context,
) -> None:
    """Show this week's volume and best set per exercise.

    The week runs Monday to Sunday. Volume is weight × reps,
    summed across all sets. Best set is the
    heaviest weight lifted, with ties broken by most reps.
    """  # ruff: ignore[ambiguous-unicode-character-docstring]
    config = _as_cli_config(ctx.obj)

    start_of_week, end_of_week = get_week_range(get_today())

    sets = db.get_sets_in_date_range(
        config.db_path, str(start_of_week), str(end_of_week)
    )

    if not sets:
        rich_print("No sets logged this week yet.")
    else:
        volume = get_volume(sets)
        rich_print(f"Total volume this week: [bold]{volume:,g}[/bold] lbs")

        best_sets = get_best_sets(sets)

        show_table(
            f"Best sets · {start_of_week.strftime('%b %-d')} – {end_of_week.strftime('%b %-d')}",  # ruff: ignore[ambiguous-unicode-character-string]
            best_sets,
        )


@app.command()
def recent(
    ctx: typer.Context,
    limit: Annotated[int, typer.Option(help="Number of sets to show.")] = 10,
) -> None:
    """Show your most recent sets, newest first."""
    config = _as_cli_config(ctx.obj)

    sets = db.get_recent_sets(config.db_path, limit)

    if not sets:
        rich_print("No sets logged yet.")
    else:
        show_table(f"Last {len(sets)} set{'s' if len(sets) != 1 else ''}", sets)
