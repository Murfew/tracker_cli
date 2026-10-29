from datetime import date

import pytest
from tests.cli.helpers import AddSet, get_output_table_rows
from typer.testing import CliRunner

from tracker_cli.cli import app


def test_prints_fallback_message_when_no_sets_logged(runner: CliRunner) -> None:
    result = runner.invoke(app, ["week"])
    assert result.exit_code == 0
    assert "No sets logged this week" in result.output


def test_prints_fallback_message_when_no_sets_logged_this_week(
    runner: CliRunner, add_set: AddSet, fixed_today: date
) -> None:
    add_set(day=date.fromisoformat("2026-10-11"))

    result = runner.invoke(app, ["week"])
    assert result.exit_code == 0
    assert "No sets logged this week" in result.output


@pytest.mark.parametrize(
    "log_date",
    [
        pytest.param(
            date.fromisoformat("2026-10-19"),
            id="first day of the week",
        ),
        pytest.param(
            date.fromisoformat("2026-10-22"),
            id="midweek",
        ),
        pytest.param(
            date.fromisoformat("2026-10-25"),
            id="last day of the week",
        ),
    ],
)
def test_includes_set_logged_within_week_boundaries(
    runner: CliRunner, add_set: AddSet, log_date: date
) -> None:
    add_set(day=log_date)

    result = runner.invoke(app, ["week"])
    assert result.exit_code == 0

    rows = get_output_table_rows(result.output)
    assert rows == [["Bench Press", "185", "12", log_date.strftime("%a %b %-d")]]


@pytest.mark.parametrize(
    "log_date",
    [
        pytest.param(
            date.fromisoformat("2026-10-18"),
            id="day before week starts",
        ),
        pytest.param(
            date.fromisoformat("2026-10-26"),
            id="day after week ends",
        ),
    ],
)
def test_excludes_set_logged_outside_week_boundaries(
    runner: CliRunner, add_set: AddSet, log_date: date
) -> None:
    add_set(day=log_date)

    result = runner.invoke(app, ["week"])
    assert result.exit_code == 0

    rows = get_output_table_rows(result.output)
    assert rows == []


def test_volume_sums_weight_times_reps_across_all_exercises(
    runner: CliRunner, add_set: AddSet
) -> None:
    add_set(weight=100, reps=10)
    add_set(weight=100, reps=8)
    add_set(weight=100, reps=2)

    result = runner.invoke(app, ["week"])
    assert result.exit_code == 0
    assert "Total volume this week: 2,000 lbs" in result.output


@pytest.mark.parametrize(
    ("logged_first", "logged_second", "best"),
    [
        pytest.param((100, 10), (200, 5), (200, 5), id="heavier set second"),
        pytest.param((100, 10), (100, 12), (100, 12), id="using reps as tie breaker"),
        pytest.param((200, 5), (100, 10), (200, 5), id="lighter set second"),
    ],
)
def test_best_set_selection(  # ruff: ignore[too-many-positional-arguments]
    runner: CliRunner,
    add_set: AddSet,
    fixed_today: date,
    logged_first: tuple[int, int],
    logged_second: tuple[int, int],
    best: tuple[int, int],
) -> None:
    add_set(weight=logged_first[0], reps=logged_first[1])
    add_set(weight=logged_second[0], reps=logged_second[1])

    result = runner.invoke(app, ["week"])
    assert result.exit_code == 0

    rows = get_output_table_rows(result.output)
    assert rows == [
        [
            "Bench Press",
            str(best[0]),
            str(best[1]),
            fixed_today.strftime("%a %b %-d"),
        ]
    ]


def test_shows_best_set_for_each_exercise(
    runner: CliRunner, add_set: AddSet, fixed_today: date
) -> None:
    add_set(name="bench press", weight=200, reps=10)
    add_set(name="bench press", weight=200, reps=8)

    add_set(name="squat", weight=400, reps=10)
    add_set(name="squat", weight=400, reps=8)

    result = runner.invoke(app, ["week"])
    assert result.exit_code == 0

    rows = get_output_table_rows(result.output)
    assert rows == [
        ["Bench Press", "200", "10", fixed_today.strftime("%a %b %-d")],
        ["Squat", "400", "10", fixed_today.strftime("%a %b %-d")],
    ]
