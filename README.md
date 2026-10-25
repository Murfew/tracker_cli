# tracker_cli

A CLI workout tracker that lets you record a set, view your recent sets, and see this week's total volume and best set per exercise.

```text
$ uv run tracker week
Total volume this week: 7,875 lbs
             Best sets · Oct 19 – Oct 25
┏━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━┳━━━━━━━━━━━━┓
┃ Exercise       ┃ Weight (lbs) ┃ Reps ┃    Date    ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━╇━━━━━━━━━━━━┩
│ Squat          │          235 │    3 │ Fri Oct 23 │
│ Bench Press    │          190 │    5 │ Fri Oct 23 │
│ Deadlift       │          315 │    5 │ Wed Oct 21 │
│ Overhead Press │          115 │    6 │ Wed Oct 21 │
└────────────────┴──────────────┴──────┴────────────┘
```

## Installation

Requires Python 3.14+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/Murfew/tracker_cli.git
cd tracker_cli
uv sync
```

## Usage

```bash
uv run tracker --help
```

Log a set:

```bash
uv run tracker log "bench press" --weight 185 --reps 8
```

Log a set for a past date:

```bash
uv run tracker log squat --weight 225 --reps 5 --day 2026-10-20
```

View your most recent sets:

```bash
uv run tracker recent --limit 10
```

See this week's total volume and best set per exercise:

```bash
uv run tracker week
```

Volume is weight × reps, summed across all sets. Your best set is your heaviest one, with ties going to the set with more reps.

Run `uv run tracker <command> --help` for all options on a given command.

## Where your data lives

Sets are stored in a local SQLite file, `app.db`, in the directory you run the command from.
To use a different file, pass `--db` before the command, or set `APP_DB_PATH`:

```bash
uv run tracker --db ~/lifts.db recent
APP_DB_PATH=~/lifts.db uv run tracker week
```

## Testing

```bash
uv run pytest
```
