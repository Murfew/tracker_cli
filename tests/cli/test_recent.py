from datetime import date
from math import nan

import pytest
from tests.cli.helpers import (
    NON_NEGATIVE_ERROR,
    OVER_UPPER_BOUND_ERROR,
    AddSet,
    get_output_table_rows,
)
from typer.testing import CliRunner

from tracker_cli.cli import UPPER_BOUND, app


def test_prints_fallback_message_when_no_sets_logged(runner: CliRunner) -> None:
    result = runner.invoke(app, ["recent"])
    assert result.exit_code == 0
    assert "No sets logged yet." in result.output


def test_shows_newest_first_across_different_days(
    runner: CliRunner, add_set: AddSet
) -> None:
    add_set(name="bench press", day=date.fromisoformat("2026-10-25"))
    add_set(name="squat", day=date.fromisoformat("2026-10-24"))
    add_set(name="shoulder press", day=date.fromisoformat("2026-10-26"))

    result = runner.invoke(app, ["recent"])
    assert result.exit_code == 0

    names = [row[0] for row in get_output_table_rows(result.output)]
    assert names == ["Shoulder Press", "Bench Press", "Squat"]


def test_shows_newest_first_on_same_day(runner: CliRunner, add_set: AddSet) -> None:
    add_set(name="bench press")
    add_set(name="squat")
    add_set(name="shoulder press")

    result = runner.invoke(app, ["recent"])
    assert result.exit_code == 0

    names = [row[0] for row in get_output_table_rows(result.output)]
    assert names == ["Shoulder Press", "Squat", "Bench Press"]


def test_limit_option_shows_only_newest_n_sets(
    runner: CliRunner, add_set: AddSet
) -> None:
    add_set(name="bench press")
    add_set(name="squat")
    add_set(name="shoulder press")

    result = runner.invoke(app, ["recent", "--limit", "2"])
    assert result.exit_code == 0

    names = [row[0] for row in get_output_table_rows(result.output)]
    assert names == ["Shoulder Press", "Squat"]


@pytest.mark.parametrize(("limit", "title"), [(1, "Last 1 set"), (2, "Last 2 sets")])
def test_table_title_matches_set_count(
    runner: CliRunner, add_set: AddSet, limit: int, title: str
) -> None:
    add_set(name="bench press")
    add_set(name="squat")
    add_set(name="shoulder press")

    result = runner.invoke(app, ["recent", "--limit", str(limit)])
    assert result.exit_code == 0

    title_line = result.output.splitlines()[0].strip()
    assert title_line == title


@pytest.mark.parametrize(
    ("limit", "message"),
    [
        pytest.param(-1, NON_NEGATIVE_ERROR, id="negative"),
        pytest.param(nan, "'nan' is not a valid int.", id="nan"),
        pytest.param(2.5, "'2.5' is not a valid int.", id="fraction"),
        pytest.param(
            UPPER_BOUND + 1, OVER_UPPER_BOUND_ERROR, id="greater than upper bound"
        ),
    ],
)
def test_rejects_invalid_limit(runner: CliRunner, limit: float, message: str) -> None:
    result = runner.invoke(app, ["recent", "--limit", str(limit)])
    assert result.exit_code == 2
    assert f"Invalid value for '--limit': {message}" in result.output


def test_limit_zero_shows_empty_table(runner: CliRunner) -> None:
    result = runner.invoke(app, ["recent", "--limit", "0"])
    assert result.exit_code == 0

    title = result.output.splitlines()[0].strip()
    assert title == "Last 0 sets"

    table_rows = get_output_table_rows(result.output)
    assert len(table_rows) == 0
