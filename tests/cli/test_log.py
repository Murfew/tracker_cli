from datetime import date
from math import inf, nan
from pathlib import Path

import pytest
from tests.cli.helpers import NON_NEGATIVE_ERROR, OVER_UPPER_BOUND_ERROR
from typer.testing import CliRunner

from tracker_cli import db
from tracker_cli.cli import UPPER_BOUND, app

BENCH_PRESS_SUGGESTION = "Did you mean 'bench press'?"

pytestmark = pytest.mark.usefixtures("register_bench_press_exercise")


def test_prints_success_message_with_title_cased_name(runner: CliRunner) -> None:
    result = runner.invoke(
        app, ["log", "bench press", "--weight", "185", "--reps", "8"]
    )
    assert result.exit_code == 0
    assert "✓ Logged Bench Press: 185 lbs × 8" in result.output


@pytest.mark.parametrize(
    "name", ["Bench Press", "   bench press   ", "BeNCh PResS", "  bEncH prESs  "]
)
def test_set_is_saved_with_normalized_name(
    runner: CliRunner, temp_db: Path, name: str
) -> None:
    result = runner.invoke(app, ["log", name, "--weight", "185", "--reps", "8"])
    assert result.exit_code == 0

    sets = db.get_recent_sets(temp_db, 1)
    assert len(sets) == 1

    assert sets[0].weight == 185
    assert sets[0].reps == 8
    assert sets[0].exercise_name == "bench press"


def test_date_is_saved_when_day_option_provided(
    runner: CliRunner, temp_db: Path
) -> None:
    result = runner.invoke(
        app,
        [
            "log",
            "Bench Press",
            "--weight",
            "185",
            "--reps",
            "8",
            "--day",
            "2026-10-25",
        ],
    )
    assert result.exit_code == 0

    db_rows = db.get_recent_sets(temp_db, 1)
    assert len(db_rows) == 1

    last_set = db_rows[0]
    assert last_set.day == date.fromisoformat("2026-10-25")


def test_day_defaults_to_today(
    runner: CliRunner, temp_db: Path, fixed_today: date
) -> None:
    result = runner.invoke(
        app, ["log", "Bench Press", "--weight", "185", "--reps", "8"]
    )
    assert result.exit_code == 0

    db_rows = db.get_recent_sets(temp_db, 1)
    assert len(db_rows) == 1

    last_set = db_rows[0]
    assert last_set.day == fixed_today


@pytest.mark.parametrize(
    "bad_date",
    [
        "2026/10/25",
        "25-10-2026",
        "2026-13-25",
        "2026-04-31",
        "2026-02-29",
    ],
)
def test_rejects_bad_date_format(runner: CliRunner, bad_date: str) -> None:
    result = runner.invoke(
        app,
        [
            "log",
            "Bench Press",
            "--weight",
            "185",
            "--reps",
            "8",
            "--day",
            bad_date,
        ],
    )
    assert result.exit_code == 2
    assert "Invalid value for '--day'" in result.output


@pytest.mark.parametrize(
    ("missing", "cli_args"),
    [
        (
            "--weight",
            [
                "log",
                "Bench Press",
                "--reps",
                "8",
            ],
        ),
        (
            "--reps",
            [
                "log",
                "Bench Press",
                "--weight",
                "185",
            ],
        ),
    ],
)
def test_rejects_missing_required_option(
    runner: CliRunner, missing: str, cli_args: list[str]
) -> None:
    result = runner.invoke(app, cli_args)
    assert result.exit_code == 2
    assert f"Missing option '{missing}'." in result.output


def test_rejects_unknown_exercise(runner: CliRunner) -> None:
    result = runner.invoke(app, ["log", "squat", "--weight", "185", "--reps", "12"])
    assert result.exit_code == 1
    assert "× Exercise does not exist." in result.output


def test_unknown_exercise_is_not_saved(runner: CliRunner, temp_db: Path) -> None:
    result = runner.invoke(app, ["log", "squat", "--weight", "185", "--reps", "12"])
    assert result.exit_code == 1

    sets = db.get_recent_sets(temp_db, 1)
    assert len(sets) == 0


def test_rejects_blank_name(runner: CliRunner) -> None:
    result = runner.invoke(app, ["log", "", "--weight", "185", "--reps", "12"])
    assert result.exit_code == 2
    assert "Invalid value for 'name': Value must not be empty." in result.output


def test_shows_suggestion_when_name_has_close_match(runner: CliRunner) -> None:
    result = runner.invoke(
        app, ["log", "banch press", "--weight", "185", "--reps", "12"]
    )
    assert BENCH_PRESS_SUGGESTION in result.output


def test_does_not_show_suggestion_when_name_has_no_close_match(
    runner: CliRunner,
) -> None:
    result = runner.invoke(app, ["log", "squat", "--weight", "185", "--reps", "12"])
    assert BENCH_PRESS_SUGGESTION not in result.output


@pytest.mark.parametrize(
    ("weight", "reps", "option", "message"),
    [
        pytest.param(
            UPPER_BOUND + 1,
            8,
            "--weight",
            OVER_UPPER_BOUND_ERROR,
            id="weight greater than upper bound",
        ),
        pytest.param(
            100,
            UPPER_BOUND + 1,
            "--reps",
            OVER_UPPER_BOUND_ERROR,
            id="reps greater than upper bound",
        ),
        pytest.param(
            -1,
            8,
            "--weight",
            NON_NEGATIVE_ERROR,
            id="negative weight",
        ),
        pytest.param(
            -0.5,
            8,
            "--weight",
            NON_NEGATIVE_ERROR,
            id="negative fraction weight",
        ),
        pytest.param(
            nan,
            8,
            "--weight",
            NON_NEGATIVE_ERROR,
            id="nan weight",
        ),
        pytest.param(
            inf,
            8,
            "--weight",
            NON_NEGATIVE_ERROR,
            id="inf weight",
        ),
        pytest.param(
            185,
            -1,
            "--reps",
            NON_NEGATIVE_ERROR,
            id="negative reps",
        ),
        pytest.param(185, nan, "--reps", "'nan' is not a valid int.", id="nan reps"),
        pytest.param(
            185, 1.5, "--reps", "'1.5' is not a valid int.", id="fraction reps"
        ),
    ],
)
def test_rejects_invalid_weight_or_reps(
    runner: CliRunner, weight: float, reps: int, option: str, message: str
) -> None:
    result = runner.invoke(
        app,
        ["log", "bench press", "--weight", str(weight), "--reps", str(reps)],
    )
    assert result.exit_code == 2
    assert f"Invalid value for '{option}': {message}" in result.output


@pytest.mark.parametrize(
    ("weight", "reps"),
    [
        pytest.param(0, 8, id="zero weight"),
        pytest.param(185, 0, id="zero reps"),
    ],
)
def test_accepts_zero_boundary(runner: CliRunner, weight: float, reps: int) -> None:
    result = runner.invoke(
        app, ["log", "bench press", "--weight", str(weight), "--reps", str(reps)]
    )
    assert result.exit_code == 0
