from pathlib import Path

import pytest
from typer.testing import CliRunner

from tracker_cli import db
from tracker_cli.cli import app


def test_prints_success_message_with_title_cased_name(runner: CliRunner) -> None:
    result = runner.invoke(app, ["exercise", "add", "bench press"])
    assert result.exit_code == 0
    assert "✓ Added Bench Press. You can now log sets for it." in result.output


@pytest.mark.parametrize(
    "name", ["bench press", "   bench press   ", "BeNCh PResS", "  bEncH prESs  "]
)
def test_exercise_is_saved_with_normalized_name(
    runner: CliRunner, temp_db: Path, name: str
) -> None:
    exercises_before = db.get_exercises(temp_db)
    assert len(exercises_before) == 0

    result = runner.invoke(app, ["exercise", "add", name])
    assert result.exit_code == 0

    exercises_after = db.get_exercises(temp_db)
    assert len(exercises_after) == 1
    assert exercises_after[0].name == "bench press"


@pytest.mark.parametrize(
    "duplicate",
    ["bench press", "   bench press   ", "BeNCh PResS", "  bEncH prESs  "],
)
def test_rejects_duplicate_exercise(runner: CliRunner, duplicate: str) -> None:
    runner.invoke(app, ["exercise", "add", "bench press"])
    result = runner.invoke(app, ["exercise", "add", duplicate])
    assert result.exit_code == 1
    assert "× Bench Press is already registered." in result.output


def test_duplicate_is_not_saved_twice(runner: CliRunner, temp_db: Path) -> None:
    runner.invoke(app, ["exercise", "add", "bench press"])
    exercises = db.get_exercises(temp_db)
    assert len(exercises) == 1

    result = runner.invoke(app, ["exercise", "add", "bench press"])
    assert result.exit_code == 1

    exercises = db.get_exercises(temp_db)
    assert len(exercises) == 1


def test_rejects_missing_name(runner: CliRunner) -> None:
    result = runner.invoke(app, ["exercise", "add"])
    assert result.exit_code == 2
    assert "Missing argument 'name'." in result.output


def test_rejects_blank_name(runner: CliRunner) -> None:
    result = runner.invoke(app, ["exercise", "add", ""])
    assert result.exit_code == 2
    assert "Invalid value for 'name': Value must not be empty." in result.output
