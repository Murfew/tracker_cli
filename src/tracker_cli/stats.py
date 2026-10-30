import difflib
from datetime import date, timedelta

from tracker_cli.db import LoggedSet


def get_volume(sets: list[LoggedSet]) -> float:
    """Calculate total volume: weight × reps, summed across all sets.

    Args:
        sets: Sets to include. Can be empty.

    Returns:
        Total volume in lbs, or 0 if there are no sets.
    """
    return sum(logged_set.weight * logged_set.reps for logged_set in sets)


def _rank(logged_set: LoggedSet) -> tuple[float, int, int]:
    """Score a set so that a better set gets a bigger score.

    Scores compare by weight first, then reps, then day. The day is negated
    so that an earlier date scores higher.

    Args:
        logged_set: The set to score.

    Returns:
        A tuple of (weight, reps, negated day), meant for comparing with
        `<` or `>`, not for display.
    """
    return (logged_set.weight, logged_set.reps, -logged_set.day.toordinal())


def get_best_sets(sets: list[LoggedSet]) -> list[LoggedSet]:
    """Find the best set for each exercise.

    The best set is the heaviest weight lifted, with ties broken by most reps.
    If two sets tie on both, the one done on the earlier day wins. If they
    were also done on the same day, the first one in `sets` wins.

    Args:
        sets: Sets to search, for any number of exercises.

    Returns:
        One set per exercise, in the order each exercise first appears in `sets`.
    """
    best: dict[str, LoggedSet] = {}
    for logged_set in sets:
        current = best.get(logged_set.exercise_name)

        if current is None or _rank(current) < _rank(logged_set):
            best[logged_set.exercise_name] = logged_set

    return list(best.values())


def get_week_range(day: date) -> tuple[date, date]:
    """Return the Monday and Sunday of the week containing a date.

    Args:
        day: Any date in the week. Passed in, not read from the clock, so
            tests can pick the date.

    Returns:
        The week's first day (Monday) and last day (Sunday), both inclusive.
    """
    start = day - timedelta(days=day.weekday())
    end = start + timedelta(days=6)
    return (start, end)


def get_closest_match(word: str, possibilities: list[str]) -> str | None:
    """Find the closest match for a word, such as a mistyped exercise name.

    Args:
        word: The word to look up.
        possibilities: Words it may match.

    Returns:
        `word` itself if it is in `possibilities`, otherwise the closest
        similar word, or None if nothing is similar enough.
    """
    if word in possibilities:
        return word

    matches = difflib.get_close_matches(word, possibilities, n=1, cutoff=0.6)

    return matches[0] if matches else None
