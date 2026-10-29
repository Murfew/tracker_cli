from collections.abc import Callable
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tracker_cli import db
from tracker_cli.cli import app

DATABASE_ERROR = "× Error: Unable to connect to database."  # ruff: ignore[ambiguous-unicode-character-string]


def _file_blocking_parent_folder(folder: Path) -> Path:
    blocker = folder / "blocker"
    blocker.touch()
    return blocker / "app.db"


def _folder_at_db_path(folder: Path) -> Path:
    path = folder / "database"
    path.mkdir()
    return path


def _junk_file_at_db_path(folder: Path) -> Path:
    path = folder / "bad.db"
    path.write_text("not sqlite")
    return path


def test_creates_missing_parent_folders(runner: CliRunner, tmp_path: Path) -> None:
    db_path = tmp_path / "data" / "db" / "test.db"
    result = runner.invoke(app, ["--db", str(db_path), "recent"])
    assert result.exit_code == 0
    assert db_path.is_file()


def test_db_option_overrides_env_var(
    runner: CliRunner, tmp_path: Path, temp_db: Path
) -> None:
    db_path = tmp_path / "data" / "test.db"
    result = runner.invoke(app, ["--db", str(db_path), "exercise", "add", "squat"])
    assert result.exit_code == 0
    assert db.get_exercise_by_name(temp_db, "squat") is None
    assert db.get_exercise_by_name(db_path, "squat") is not None


@pytest.mark.parametrize(
    ("make_db_path", "message"),
    [
        pytest.param(
            _file_blocking_parent_folder,
            "× Error: A regular file already exists at this exact path location.",  # ruff: ignore[ambiguous-unicode-character-string]
            id="file where parent folder should be",
        ),
        pytest.param(
            _folder_at_db_path,
            DATABASE_ERROR,
            id="folder instead of file",
        ),
        pytest.param(
            _junk_file_at_db_path,
            DATABASE_ERROR,
            id="file is not a database",
        ),
    ],
)
def test_rejects_unusable_db_path(
    runner: CliRunner,
    tmp_path: Path,
    make_db_path: Callable[[Path], Path],
    message: str,
) -> None:
    bad_path = make_db_path(tmp_path)
    result = runner.invoke(app, ["--db", str(bad_path), "recent"])
    assert result.exit_code == 1
    assert message in result.output
