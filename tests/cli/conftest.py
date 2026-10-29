from datetime import date
from pathlib import Path

import pytest
from rich.console import Console
from tests.cli.helpers import AddSet
from typer.testing import CliRunner

import tracker_cli.cli
from tracker_cli import db

TODAY = date.fromisoformat("2026-10-24")


@pytest.fixture(autouse=True)
def temp_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("APP_DB_PATH", str(db_path))
    db.init_db(db_path)
    return db_path


@pytest.fixture(autouse=True)
def setup_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COLUMNS", "1000")
    monkeypatch.setenv("TERMINAL_WIDTH", "1000")
    monkeypatch.setattr(
        tracker_cli.cli,
        "console",
        Console(force_terminal=False, color_system=None),
    )


@pytest.fixture
def add_set(temp_db: Path, fixed_today: date) -> AddSet:
    def _add_set(
        name: str = "bench press",
        weight: float = 185,
        reps: int = 12,
        day: date | None = None,
    ) -> None:
        exercise = db.create_exercise(temp_db, name)
        if exercise is None:
            exercise = db.get_exercise_by_name(temp_db, name)
        assert exercise is not None

        if day is None:
            day = fixed_today
        db.create_set(temp_db, weight, reps, day, exercise.id)

    return _add_set


@pytest.fixture
def register_bench_press_exercise(temp_db: Path) -> None:
    db.create_exercise(temp_db, "bench press")


@pytest.fixture
def fixed_today(monkeypatch: pytest.MonkeyPatch) -> date:
    monkeypatch.setattr(tracker_cli.cli, "get_today", lambda: TODAY)
    return TODAY


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()
