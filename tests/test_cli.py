from datetime import date
from pathlib import Path
from typing import Protocol

import pytest
from pytest import MonkeyPatch
from typer.testing import CliRunner

from tracker_cli import db
from tracker_cli.cli import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def temp_db(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("APP_DB_PATH", str(tmp_path / "test.db"))


class AddSet(Protocol):
    def __call__(
        self,
        name: str = ...,
        weight: float = ...,
        reps: int = ...,
        day: date | None = ...,
    ) -> None: ...


@pytest.fixture
def add_set(temp_db: None) -> AddSet:
    db.init_db()

    def _add_set(
        name: str = "bench press",
        weight: float = 185,
        reps: int = 12,
        day: date | None = None,
    ) -> None:
        if day is None:
            day = date.today()  # noqa: DTZ011
        db.create_set(name, weight, reps, day)

    return _add_set


class TestLog:
    def test_prints_success_message(self):
        result = runner.invoke(
            app, ["log", "Bench Press", "--weight", "185", "--reps", "8"]
        )
        assert result.exit_code == 0
        assert "✓ Logged Bench Press: 185 lbs × 8" in result.output  # noqa: RUF001

    def test_set_is_saved(self):
        result = runner.invoke(
            app, ["log", "Bench Press", "--weight", "185", "--reps", "8"]
        )
        assert result.exit_code == 0

        db_rows = db.get_recent_sets(1)
        assert len(db_rows) == 1

        last_set = db_rows[0]
        assert last_set.weight == 185
        assert last_set.reps == 8

    @pytest.mark.parametrize(
        "messy_name", ["   bench press   ", "BeNCh PResS", "  bEncH prESs  "]
    )
    def test_exercise_name_is_normalized(self, messy_name: str):
        result = runner.invoke(
            app, ["log", messy_name, "--weight", "185", "--reps", "8"]
        )
        assert result.exit_code == 0

        db_rows = db.get_recent_sets(1)
        assert len(db_rows) == 1

        last_set = db_rows[0]
        assert last_set.exercise_name == "bench press"

    def test_date_is_saved_when_day_option_provided(self):
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

        db_rows = db.get_recent_sets(1)
        assert len(db_rows) == 1

        last_set = db_rows[0]
        assert last_set.day == date.fromisoformat("2026-10-25")

    def test_day_defaults_to_today(self):
        result = runner.invoke(
            app, ["log", "Bench Press", "--weight", "185", "--reps", "8"]
        )
        assert result.exit_code == 0

        db_rows = db.get_recent_sets(1)
        assert len(db_rows) == 1

        last_set = db_rows[0]
        assert last_set.day == date.today()  # noqa: DTZ011

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
    def test_rejects_bad_date_format(self, bad_date: str):
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
        "missing, cli_args",
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
    def test_rejects_missing_required_option(self, missing: str, cli_args: list[str]):
        result = runner.invoke(app, cli_args)
        assert result.exit_code == 2
        assert f"Missing option '{missing}'." in result.output


class TestWeek:
    @pytest.mark.skip
    def test_prints_fallback_message_when_no_sets_logged(self): ...

    @pytest.mark.skip
    def test_prints_fallback_message_when_no_sets_logged_this_week(self): ...

    @pytest.mark.skip
    def test_includes_set_logged_this_monday(self): ...

    @pytest.mark.skip
    def test_excludes_set_logged_last_sunday(self): ...

    @pytest.mark.skip
    def test_volume_sums_weight_times_reps_across_all_exercises(self): ...

    # Parametrize (chooses heavier set logged later, chooses more reps when weight is equal, keeps best set when lighter set logged after)
    @pytest.mark.skip
    def test_best_set_selection(self): ...

    @pytest.mark.skip
    def test_shows_best_set_for_each_exercise(self): ...


class TestRecent:
    def test_prints_fallback_message_when_no_sets_logged(self):
        result = runner.invoke(app, ["recent"])
        assert result.exit_code == 0
        assert "No sets logged yet." in result.output

    def test_shows_newest_first_across_different_days(self, add_set: AddSet):
        add_set(name="bench press", day=date.fromisoformat("2026-10-25"))
        add_set(name="squat", day=date.fromisoformat("2026-10-24"))
        add_set(name="shoulder press", day=date.fromisoformat("2026-10-26"))

        result = runner.invoke(app, ["recent"])
        assert result.exit_code == 0

        bench_press = result.output.index("Bench Press")
        squat = result.output.index("Squat")
        shoulder_press = result.output.index("Shoulder Press")
        assert shoulder_press < bench_press < squat

    def test_shows_newest_first_on_same_day(self, add_set: AddSet):
        add_set(name="bench press")
        add_set(name="squat")
        add_set(name="shoulder press")

        result = runner.invoke(app, ["recent"])
        assert result.exit_code == 0

        bench_press = result.output.index("Bench Press")
        squat = result.output.index("Squat")
        shoulder_press = result.output.index("Shoulder Press")
        assert shoulder_press < squat < bench_press

    def test_limit_option_shows_only_newest_n_sets(self, add_set: AddSet):
        add_set(name="bench press")
        add_set(name="squat")
        add_set(name="shoulder press")

        result = runner.invoke(app, ["recent", "--limit", "2"])
        assert result.exit_code == 0

        squat = result.output.index("Squat")
        shoulder_press = result.output.index("Shoulder Press")
        assert shoulder_press < squat
        assert "Bench Press" not in result.output

    @pytest.mark.parametrize("limit, title", [(1, "Last 1 set"), (2, "Last 2 sets")])
    def test_table_title_matches_set_count(
        self, add_set: AddSet, limit: int, title: str
    ):
        add_set(name="bench press")
        add_set(name="squat")
        add_set(name="shoulder press")

        result = runner.invoke(app, ["recent", "--limit", str(limit)])
        assert result.exit_code == 0

        title_line = result.output.splitlines()[0].strip()
        assert title_line == title
