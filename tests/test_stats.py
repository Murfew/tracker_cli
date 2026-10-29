from datetime import date

import pytest

from tracker_cli.db import LoggedSet
from tracker_cli.stats import (
    get_best_sets,
    get_closest_match,
    get_volume,
    get_week_range,
)

EARLIER_DAY = ANY_DAY = date.fromisoformat("2026-10-28")
LATER_DAY = date.fromisoformat("2026-11-28")


class TestGetVolume:
    @pytest.mark.parametrize(
        ("sets", "expected_volume"),
        [
            pytest.param([], 0, id="no sets"),
            pytest.param(
                [LoggedSet("bench press", 100, 10, ANY_DAY)],
                1000,
                id="one set",
            ),
            pytest.param(
                [
                    LoggedSet("bench press", 100, 10, ANY_DAY),
                    LoggedSet("squat", 100, 10, ANY_DAY),
                    LoggedSet("shoulder press", 100, 10, ANY_DAY),
                ],
                3000,
                id="several sets",
            ),
            pytest.param(
                [
                    LoggedSet("bench press", 102.5, 10, ANY_DAY),
                    LoggedSet("squat", 112.5, 10, ANY_DAY),
                ],
                2150,
                id="fractional weight",
            ),
            pytest.param(
                [
                    LoggedSet("bench press", 100, 0, ANY_DAY),
                ],
                0,
                id="zero reps",
            ),
            pytest.param(
                [LoggedSet("bench press", 0, 10, ANY_DAY)],
                0,
                id="zero weight",
            ),
        ],
    )
    def test_returns_total(self, sets: list[LoggedSet], expected_volume: float) -> None:
        volume = get_volume(sets)
        assert volume == expected_volume


class TestGetBestSets:
    @pytest.mark.parametrize(
        ("sets", "expected_bests"),
        [
            pytest.param(
                [
                    LoggedSet("bench press", 100, 10, ANY_DAY),
                    LoggedSet("bench press", 200, 10, ANY_DAY),
                ],
                [
                    LoggedSet("bench press", 200, 10, ANY_DAY),
                ],
                id="heavier weight wins",
            ),
            pytest.param(
                [
                    LoggedSet("bench press", 100, 10, ANY_DAY),
                    LoggedSet("bench press", 100, 12, ANY_DAY),
                ],
                [
                    LoggedSet("bench press", 100, 12, ANY_DAY),
                ],
                id="more reps breaks the tie",
            ),
            pytest.param(
                [
                    LoggedSet("bench press", 100, 12, ANY_DAY),
                    LoggedSet("bench press", 200, 10, ANY_DAY),
                ],
                [
                    LoggedSet("bench press", 200, 10, ANY_DAY),
                ],
                id="heavier beats more reps",
            ),
            pytest.param(
                [
                    LoggedSet("bench press", 100, 10, EARLIER_DAY),
                    LoggedSet("bench press", 100, 10, LATER_DAY),
                ],
                [
                    LoggedSet("bench press", 100, 10, EARLIER_DAY),
                ],
                id="earlier wins full tie",
            ),
        ],
    )
    def test_picks_best_for_one_exercise(
        self, sets: list[LoggedSet], expected_bests: list[LoggedSet]
    ) -> None:
        best = get_best_sets(sets)
        assert best == expected_bests

    def test_returns_empty_list_for_no_sets(self) -> None:
        best = get_best_sets([])
        assert best == []

    def test_returns_one_per_exercise_in_first_seen_order(
        self,
    ) -> None:
        sets = [
            LoggedSet("bench press", 100, 12, ANY_DAY),
            LoggedSet("bench press", 200, 12, ANY_DAY),
            LoggedSet("squat", 100, 12, ANY_DAY),
        ]
        expected = [
            LoggedSet("bench press", 200, 12, ANY_DAY),
            LoggedSet("squat", 100, 12, ANY_DAY),
        ]

        best = get_best_sets(sets)
        assert best == expected


class TestGetWeekRange:
    WEEK_OF_OCT_19 = (
        date.fromisoformat("2026-10-19"),
        date.fromisoformat("2026-10-25"),
    )

    @pytest.mark.parametrize(
        ("day", "expected_range"),
        [
            pytest.param(
                date.fromisoformat("2026-10-19"),
                WEEK_OF_OCT_19,
                id="monday",
            ),
            pytest.param(
                date.fromisoformat("2026-10-25"),
                WEEK_OF_OCT_19,
                id="sunday",
            ),
            pytest.param(
                date.fromisoformat("2026-10-22"),
                WEEK_OF_OCT_19,
                id="midweek",
            ),
            pytest.param(
                date.fromisoformat("2026-10-28"),
                (date.fromisoformat("2026-10-26"), date.fromisoformat("2026-11-01")),
                id="crosses month",
            ),
            pytest.param(
                date.fromisoformat("2027-01-01"),
                (date.fromisoformat("2026-12-28"), date.fromisoformat("2027-01-03")),
                id="crosses year",
            ),
        ],
    )
    def test_returns_monday_to_sunday(
        self, day: date, expected_range: tuple[date, date]
    ) -> None:
        week_range = get_week_range(day)
        assert week_range == expected_range


class TestGetClosestMatch:
    @pytest.mark.parametrize(
        ("word", "expected_match"),
        [
            pytest.param(
                "bench press",
                "bench press",
                id="exact match",
            ),
            pytest.param("banch press", "bench press", id="typo"),
        ],
    )
    def test_returns_match(self, word: str, expected_match: str) -> None:
        closest_match = get_closest_match(
            word,
            ["incline bench press", "bench row", "bench press"],
        )
        assert closest_match == expected_match

    @pytest.mark.parametrize(
        ("possibilities"),
        [
            pytest.param(["squat"], id="nothing similar"),
            pytest.param([], id="empty possibilities"),
        ],
    )
    def test_returns_none(self, possibilities: list[str]) -> None:
        closest_match = get_closest_match("bench press", possibilities)
        assert closest_match is None
