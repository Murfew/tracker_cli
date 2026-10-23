# tracker_cli

A CLI workout tracker that lets you record a set, view your recent sets, and see this week's total volume and best set per exercise.

## Installation

Requires Python 3.14+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/<your-username>/tracker_cli.git
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

View your most recent sets:

```bash
uv run tracker recent --limit 10
```

See this week's total volume and best set per exercise:

```bash
uv run tracker week
```

Run `uv run tracker <command> --help` for all options on a given command.

## Testing

```bash
uv run pytest
```
