import re
from datetime import date
from pathlib import Path
from typing import Protocol

import pytest
from typer.testing import CliRunner

import tracker_cli
from tracker_cli import db
from tracker_cli.cli import app

runner = CliRunner()

TODAY = date.fromisoformat("2026-10-24")
BENCH_PRESS_SUGGESTION = "Did you mean 'bench press'? [Y/n]"


@pytest.fixture(autouse=True)
def temp_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("APP_DB_PATH", db_path)
    db.init_db(db_path)
    return db_path


@pytest.fixture(autouse=True)
def wide_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COLUMNS", "1000")
    monkeypatch.setenv("TERMINAL_WIDTH", "1000")


class AddSet(Protocol):
    def __call__(
        self,
        name: str = ...,
        weight: float = ...,
        reps: int = ...,
        day: date | None = ...,
    ) -> None: ...


@pytest.fixture
def add_set(temp_db: str, fixed_today: date) -> AddSet:
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
def register_bench_press_exercise(temp_db: str) -> None:
    db.create_exercise(temp_db, "bench press")


@pytest.fixture
def fixed_today(monkeypatch: pytest.MonkeyPatch) -> date:
    monkeypatch.setattr(tracker_cli.cli, "get_today", lambda: TODAY)
    return TODAY


def get_output_table_rows(table: str) -> list[list[str]]:
    return [
        [
            item
            for item in map(
                str.strip, re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", line).split("│")
            )
            if item
        ]
        for line in table.splitlines()
        if "│" in line
    ]


class TestExerciseAdd:
    def test_prints_success_messsage_with_title_cased_name(self) -> None:
        result = runner.invoke(app, ["exercise", "add", "bench press"])
        assert result.exit_code == 0
        assert "✓ Added Bench Press. You can now log sets for it." in result.output

    @pytest.mark.parametrize(
        "name", ["bench press", "   bench press   ", "BeNCh PResS", "  bEncH prESs  "]
    )
    def test_exerise_is_saved_with_normalized_name(
        self, temp_db: str, name: str
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
    def test_rejects_duplicate_exercise(self, duplicate: str) -> None:
        runner.invoke(app, ["exercise", "add", "bench press"])
        result = runner.invoke(app, ["exercise", "add", duplicate])
        assert result.exit_code == 1
        assert "× Bench Press is already registered." in result.output  # ruff: ignore[ambiguous-unicode-character-string]

    def test_duplicate_is_not_saved_twice(self, temp_db: str) -> None:
        runner.invoke(app, ["exercise", "add", "bench press"])
        exercises = db.get_exercises(temp_db)
        assert len(exercises) == 1

        result = runner.invoke(app, ["exercise", "add", "bench press"])
        assert result.exit_code == 1

        exercises = db.get_exercises(temp_db)
        assert len(exercises) == 1

    def test_rejects_missing_name(self) -> None:
        result = runner.invoke(app, ["exercise", "add"])
        assert result.exit_code == 2
        assert "Missing argument 'name'." in result.output

    def test_rejects_blank_name(self) -> None:
        result = runner.invoke(app, ["exercise", "add", ""])
        assert result.exit_code == 2
        assert "Invalid value for 'name': Value must not be empty." in result.output


@pytest.mark.usefixtures("register_bench_press_exercise")
class TestLog:
    def test_prints_success_message_with_title_cased_name(self) -> None:
        result = runner.invoke(
            app, ["log", "bench press", "--weight", "185", "--reps", "8"]
        )
        assert result.exit_code == 0
        assert "✓ Logged Bench Press: 185 lbs × 8" in result.output  # ruff: ignore[ambiguous-unicode-character-string]

    @pytest.mark.parametrize(
        "name", ["Bench Press", "   bench press   ", "BeNCh PResS", "  bEncH prESs  "]
    )
    def test_set_is_saved_with_normalized_name(self, temp_db: str, name: str) -> None:
        result = runner.invoke(app, ["log", name, "--weight", "185", "--reps", "8"])
        assert result.exit_code == 0

        sets = db.get_recent_sets(temp_db, 1)
        assert len(sets) == 1

        assert sets[0].weight == 185
        assert sets[0].reps == 8
        assert sets[0].exercise_name == "bench press"

    def test_date_is_saved_when_day_option_provided(self, temp_db: str) -> None:
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

    def test_day_defaults_to_today(self, temp_db: str, fixed_today: date) -> None:
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
    def test_rejects_bad_date_format(self, bad_date: str) -> None:
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
        self, missing: str, cli_args: list[str]
    ) -> None:
        result = runner.invoke(app, cli_args)
        assert result.exit_code == 2
        assert f"Missing option '{missing}'." in result.output

    def test_rejects_unknown_exercise(self) -> None:
        result = runner.invoke(app, ["log", "squat", "--weight", "185", "--reps", "12"])
        assert result.exit_code == 1
        assert "× Exercise does not exist." in result.output  # ruff: ignore[ambiguous-unicode-character-string]

    def test_unknown_exercise_is_not_saved(self, temp_db: str) -> None:
        result = runner.invoke(app, ["log", "squat", "--weight", "185", "--reps", "12"])
        assert result.exit_code == 1

        sets = db.get_recent_sets(temp_db, 1)
        assert len(sets) == 0

    def test_rejects_blank_name(self) -> None:
        result = runner.invoke(app, ["log", "", "--weight", "185", "--reps", "12"])
        assert result.exit_code == 2
        assert "Invalid value for 'name': Value must not be empty." in result.output

    def test_shows_suggestion_when_name_has_close_match(self) -> None:
        result = runner.invoke(
            app, ["log", "banch press", "--weight", "185", "--reps", "12"]
        )
        assert BENCH_PRESS_SUGGESTION in result.output

    def test_does_not_show_suggestion_when_name_has_no_close_match(self) -> None:
        result = runner.invoke(app, ["log", "squat", "--weight", "185", "--reps", "12"])
        assert BENCH_PRESS_SUGGESTION not in result.output

    def test_rejects_negative_reps(self) -> None:
        result = runner.invoke(
            app, ["log", "banch press", "--weight", "185", "--reps", "-10"]
        )
        assert result.exit_code == 2
        assert (
            "Invalid value for '--reps': Value must not be negative." in result.output
        )

    def test_rejects_negative_weight(self) -> None:
        result = runner.invoke(
            app, ["log", "banch press", "--weight", "-185", "--reps", "10"]
        )
        assert result.exit_code == 2
        assert (
            "Invalid value for '--weight': Value must not be negative." in result.output
        )


class TestWeek:
    def test_prints_fallback_message_when_no_sets_logged(self) -> None:
        result = runner.invoke(app, ["week"])
        assert result.exit_code == 0
        assert "No sets logged this week" in result.output

    def test_prints_fallback_message_when_no_sets_logged_this_week(
        self, add_set: AddSet, fixed_today: date
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
        self, add_set: AddSet, log_date: date
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
        self, add_set: AddSet, log_date: date
    ) -> None:
        add_set(day=log_date)

        result = runner.invoke(app, ["week"])
        assert result.exit_code == 0

        rows = get_output_table_rows(result.output)
        assert rows == []

    def test_volume_sums_weight_times_reps_across_all_exercises(
        self, add_set: AddSet
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
            pytest.param(
                (100, 10), (100, 12), (100, 12), id="using reps as tie breaker"
            ),
            pytest.param((200, 5), (100, 10), (200, 5), id="lighter set second"),
        ],
    )
    def test_best_set_selection(
        self,
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
                TODAY.strftime("%a %b %-d"),
            ]
        ]

    def test_shows_best_set_for_each_exercise(
        self, add_set: AddSet, fixed_today: date
    ) -> None:
        add_set(name="bench press", weight=200, reps=10)
        add_set(name="bench press", weight=200, reps=8)

        add_set(name="squat", weight=400, reps=10)
        add_set(name="squat", weight=400, reps=8)

        result = runner.invoke(app, ["week"])
        assert result.exit_code == 0

        rows = get_output_table_rows(result.output)
        assert rows == [
            ["Bench Press", "200", "10", TODAY.strftime("%a %b %-d")],
            ["Squat", "400", "10", TODAY.strftime("%a %b %-d")],
        ]


class TestRecent:
    def test_prints_fallback_message_when_no_sets_logged(self) -> None:
        result = runner.invoke(app, ["recent"])
        assert result.exit_code == 0
        assert "No sets logged yet." in result.output

    def test_shows_newest_first_across_different_days(self, add_set: AddSet) -> None:
        add_set(name="bench press", day=date.fromisoformat("2026-10-25"))
        add_set(name="squat", day=date.fromisoformat("2026-10-24"))
        add_set(name="shoulder press", day=date.fromisoformat("2026-10-26"))

        result = runner.invoke(app, ["recent"])
        assert result.exit_code == 0

        names = [row[0] for row in get_output_table_rows(result.output)]
        assert names == ["Shoulder Press", "Bench Press", "Squat"]

    def test_shows_newest_first_on_same_day(self, add_set: AddSet) -> None:
        add_set(name="bench press")
        add_set(name="squat")
        add_set(name="shoulder press")

        result = runner.invoke(app, ["recent"])
        assert result.exit_code == 0

        names = [row[0] for row in get_output_table_rows(result.output)]
        assert names == ["Shoulder Press", "Squat", "Bench Press"]

    def test_limit_option_shows_only_newest_n_sets(self, add_set: AddSet) -> None:
        add_set(name="bench press")
        add_set(name="squat")
        add_set(name="shoulder press")

        result = runner.invoke(app, ["recent", "--limit", "2"])
        assert result.exit_code == 0

        names = [row[0] for row in get_output_table_rows(result.output)]
        assert names == ["Shoulder Press", "Squat"]

    @pytest.mark.parametrize(
        ("limit", "title"), [(1, "Last 1 set"), (2, "Last 2 sets")]
    )
    def test_table_title_matches_set_count(
        self, add_set: AddSet, limit: int, title: str
    ) -> None:
        add_set(name="bench press")
        add_set(name="squat")
        add_set(name="shoulder press")

        result = runner.invoke(app, ["recent", "--limit", str(limit)])
        assert result.exit_code == 0

        title_line = result.output.splitlines()[0].strip()
        assert title_line == title
