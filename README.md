# tracker_cli

A CLI workout tracker that lets you register exercises, record sets, view your recent sets, and see this week's total volume and best set per exercise.

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

Register an exercise before logging sets for it (once per exercise):

```bash
uv run tracker exercise add "bench press"
```

Exercise names ignore letter case, so `Bench Press` and `bench press` count as the same exercise.

Log a set:

```bash
uv run tracker log "bench press" --weight 185 --reps 8
```

If you mistype an exercise name, the tracker suggests the closest registered one:

```text
$ uv run tracker log "bench pres" --weight 185 --reps 8
× Exercise does not exist.
Did you mean 'bench press'? [Y/n]: y
✓ Logged Bench Press: 185 lbs × 8
```

Weight, reps and `--limit` must be between 0 and 1000; the cap catches typos like 2250 for 225.

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

The week runs Monday to Sunday. Volume is weight × reps, summed across all sets. Your best set is your heaviest one. If two sets tie on weight, the one with more reps wins; if they also tie on reps, the earlier one wins.

Run `uv run tracker <command> --help` for all options on a given command.

## Where your data lives

Exercises and sets are stored in a SQLite file in your user app folder (`~/.config/tracker-cli/app.db on Linux`), which is created the first time you run a command. To use a different file, pass `--db` before the command, or set `APP_DB_PATH`:

```bash
uv run tracker --db ~/lifts.db recent
APP_DB_PATH=~/lifts.db uv run tracker week
```

## Testing

```bash
uv run pytest
```
