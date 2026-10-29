import re
from datetime import date
from typing import Protocol

from tracker_cli.cli import UPPER_BOUND

OVER_UPPER_BOUND_ERROR = f"Value must be at most {UPPER_BOUND}."
NON_NEGATIVE_ERROR = "Value must be a finite number, zero or greater."


class AddSet(Protocol):
    def __call__(
        self,
        name: str = ...,
        weight: float = ...,
        reps: int = ...,
        day: date | None = ...,
    ) -> None: ...


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
