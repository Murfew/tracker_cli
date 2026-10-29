import math
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Annotated, NamedTuple

import typer
from rich.console import Console
from rich.table import Table

from tracker_cli import db
from tracker_cli.stats import (
    get_best_sets,
    get_closest_match,
    get_volume,
    get_week_range,
)

console = Console()

app = typer.Typer()
exercises_app = typer.Typer(help="Manage the exercises you can log sets for.")
app.add_typer(exercises_app, name="exercise")

UPPER_BOUND = 1000
DATABASE_PATH = Path(typer.get_app_dir("tracker-cli")) / "app.db"


class CliConfig(NamedTuple):
    """Settings shared by every command, stored on the Typer context.

    Attributes:
        db_path: Path to the SQLite database file.
    """

    db_path: Path


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


def _show_table(title: str, sets: list[db.LoggedSet]) -> None:
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
        Path,
        typer.Option(
            "--db",
            envvar="APP_DB_PATH",
            help="Path to the SQLite database file. Put it before the command.",
        ),
    ] = DATABASE_PATH,
) -> None:
    """Track your lifts from the terminal.

    Your sets are saved in a database file in your user app folder, which
    is created the first time you run a command. To keep the database
    somewhere else, pass --db or set APP_DB_PATH.
    """  # ruff: ignore[docstring-missing-exception]
    try:
        db_path.parent.mkdir(parents=True, exist_ok=True)
    except PermissionError as err:
        console.print(
            f"[red]×[/red] Error: Insufficient OS permissions to create this directory. Path: {db_path}"  # ruff: ignore[ambiguous-unicode-character-string]
        )
        raise typer.Exit(1) from err
    except FileExistsError as err:
        console.print(
            f"[red]×[/red] Error: A regular file already exists at this exact path location. Path: {db_path}"  # ruff: ignore[ambiguous-unicode-character-string]
        )
        raise typer.Exit(1) from err

    ctx.obj = CliConfig(db_path)

    try:
        db.init_db(db_path)
    except sqlite3.DatabaseError as err:
        console.print("[red]×[/red] Error: Unable to connect to database.")  # ruff: ignore[ambiguous-unicode-character-string]
        raise typer.Exit(1) from err


def _non_negative_number(value: float) -> float:
    """Reject negative or non-finite numbers.

    Used as a Typer callback for weight, reps and limit.

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


def _number_less_than_or_equal_to_upper_bound(value: float) -> float:
    """Reject numbers above `UPPER_BOUND`, to catch typos like 2250 for 225.

    Args:
        value: The number the user typed.

    Returns:
        The value, unchanged.

    Raises:
        typer.BadParameter: If value is greater than `UPPER_BOUND`.
    """
    if value > UPPER_BOUND:
        raise typer.BadParameter(f"Value must be at most {UPPER_BOUND}.")
    return value


def _validate_number(value: float) -> float:
    """Run every number check. Used as a Typer callback for weight, reps and limit.

    Args:
        value: The number the user typed.

    Returns:
        The value, unchanged.

    Raises:
        typer.BadParameter: If value is negative, infinite, NaN, or greater
            than `UPPER_BOUND`.
    """  # ruff: ignore[docstring-extraneous-exception]
    return _number_less_than_or_equal_to_upper_bound(_non_negative_number(value))


def _non_empty_lowercase_string(value: str) -> str:
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
            callback=_non_empty_lowercase_string,
            help='Exercise name, e.g. "bench press". Quote names with spaces.',
        ),
    ],
) -> None:
    """Register an exercise so you can log sets for it. Names ignore letter case."""  # ruff: ignore[docstring-missing-exception]
    config = _as_cli_config(ctx.obj)

    exercise = db.create_exercise(config.db_path, name)

    if exercise is None:
        console.print(f"[red]×[/red] {name.title()} is already registered.")  # ruff: ignore[ambiguous-unicode-character-string]
        raise typer.Exit(1)

    console.print(
        f"[green]✓[/green] Added {name.title()}. You can now log sets for it."
    )


@app.command()
def log(
    ctx: typer.Context,
    name: Annotated[
        str,
        typer.Argument(
            callback=_non_empty_lowercase_string,
            help='Exercise name, e.g. "bench press". Quote names with spaces.',
        ),
    ],
    weight: Annotated[
        float, typer.Option(callback=_validate_number, help="Weight lifted, in lbs.")
    ],
    reps: Annotated[
        int, typer.Option(callback=_validate_number, help="Number of reps.")
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
    # Only an exact match gets logged.
    if name_match != name:
        console.print("[red]×[/red] Exercise does not exist.")  # ruff: ignore[ambiguous-unicode-character-string]
        if name_match is not None:
            console.print(f"Did you mean '{name_match}'?")

        raise typer.Exit(1)

    exercise = exercises_by_name[name_match]
    day_as_date = get_today() if day is None else day.date()

    db.create_set(config.db_path, weight, reps, day_as_date, exercise.id)

    console.print(
        f"[green]✓[/green] Logged {exercise.name.title()}: {weight:g} lbs × {reps}"  # ruff: ignore[ambiguous-unicode-character-string]
    )


@app.command()
def week(
    ctx: typer.Context,
) -> None:
    """Show this week's volume and best set per exercise.

    The week runs Monday to Sunday. Volume is weight × reps,
    summed across all sets. Your best set is your heaviest one.
    If two sets tie on weight, the one with more reps wins;
    if they also tie on reps, the earlier one wins.
    """  # ruff: ignore[ambiguous-unicode-character-docstring]
    config = _as_cli_config(ctx.obj)

    start_of_week, end_of_week = get_week_range(get_today())

    sets = db.get_sets_in_date_range(config.db_path, start_of_week, end_of_week)

    if not sets:
        console.print("No sets logged this week yet.")
    else:
        volume = get_volume(sets)
        console.print(f"Total volume this week: [bold]{volume:,g}[/bold] lbs")

        best_sets = get_best_sets(sets)

        _show_table(
            f"Best sets · {start_of_week.strftime('%b %-d')} – {end_of_week.strftime('%b %-d')}",  # ruff: ignore[ambiguous-unicode-character-string]
            best_sets,
        )


@app.command()
def recent(
    ctx: typer.Context,
    limit: Annotated[
        int, typer.Option(callback=_validate_number, help="Number of sets to show.")
    ] = 10,
) -> None:
    """Show your most recent sets, newest first."""
    config = _as_cli_config(ctx.obj)

    sets = db.get_recent_sets(config.db_path, limit)

    if not sets and limit != 0:
        console.print("No sets logged yet.")
    else:
        _show_table(f"Last {len(sets)} set{'s' if len(sets) != 1 else ''}", sets)
