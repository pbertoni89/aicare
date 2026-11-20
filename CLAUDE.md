# CLAUDE.md

## What this is

`aicare` is a small, single-file Python wrapper around [ccusage](https://github.com/ryoppippi/ccusage).
It turns the daily Claude Code token report into an environmental report by adding three things:
session names, estimated power use (kWh), and CO2 footprint (kg).

## Files

- `aicare.py`: the whole tool. It uses only the Python standard library (3.9+ for `str.removeprefix`).
- `setup.sh`: installs Bun, which provides `bunx`, then runs ccusage once.
- `README.md`: a one-paragraph description of the project.

## Running

```bash
./setup.sh          # once: installs bun
python3 aicare.py   # prints the enriched daily table
```

`bunx` must be on `PATH`. To call ccusage directly, use `bunx ccusage claude daily [--json]`.
There are no tests, no build step and no dependencies to install.

## How aicare.py works

1. It runs `bunx ccusage claude daily --json` and reads the `daily[]` and `totals` fields.
   - Use the JSON output. Do not parse ccusage's ASCII table: its layout changes between versions, and its title box (`╭──╮`) uses `│` too, which broke the earlier line-patching approach.
2. `load_sessions_by_date()` scans the Claude Code transcripts in `~/.claude/projects/**/*.jsonl` (including `subagents/`) and in `~/.config/claude/projects`:
   - A session belongs to a date if it has an `"type":"assistant"` record with that timestamp, in the system's local timezone (ccusage uses the same default).
   - Each session's title comes from its last `custom-title` record (set by `/rename`). If there is none, the last `ai-title` is used, and if that is missing too, the first 8 characters of the session id.
   - Titles are cut to `SESSION_TITLE_MAX` characters and listed once per day.
   - Lines are checked with a substring match before `json.loads`, which keeps the scan fast (about 200 MB in under 1 s).
3. `calculate_metrics()` converts token counts into energy and CO2. Each factor is read once at import time through `env_float()`:
   - Output tokens: `WH_PER_1M_OUTPUT`, from `AICARE_ANTHROPIC_WH_PER_1M_OUTPUT`, default 1950.
   - Cache-read tokens: `WH_PER_1M_CACHE_READ`, from `AICARE_ANTHROPIC_WH_PER_1M_CACHE_READ`, default 39.
   - Input and cache-creation tokens: `WH_PER_1M_INPUT`, from `AICARE_ANTHROPIC_WH_PER_1M_INPUT`, default 240.
   - Energy to CO2: `KG_CO2_PER_KWH`, from `AICARE_GRID_KG_CO2_PER_KWH`, default 0.275.

   `env_float()` falls back to the default when a value is unset, not a number, or negative.
   These numbers are rough estimates, not measured values.
   New tunables follow the same naming: `AICARE_ANTHROPIC_*` for model energy and `AICARE_GRID_*` for the grid.
   Always read tunables with `env_float()`. It records each resolved value and its source (`env`, `default`, or `default, ignored invalid '…'`) in `ENV_SETTINGS`, and `main()` prints them as the final "Settings used:" line.
4. `render_table()` draws the box tables. Each cell is a list of lines, so a single row can stack several sessions or models.
5. `print_weekly_load()` groups daily kWh by ISO week (weeks start on Monday) and converts each week into hours of a reference load: `kWh * 1000 / W`.
   - The reference load comes from the `AICARE_EXAMPLE_ELECTRIC_LOAD` env var, in watts. The default is `DEFAULT_EXAMPLE_LOAD_W` (2000), which is also used when the value is invalid or ≤ 0.

## README

The example output in `README.md` comes from real data, with session names replaced by gibberish. Never put real session titles in the README, because they can reveal client and project names.

## Caveats

- Token, cost, power and CO2 figures are **per day**, not per session. The Session column only lists which sessions were active that day.
- Session names come from Claude Code's internal JSONL record types (`custom-title`, `ai-title`), which are undocumented and may change.
- Column widths use `len()`, so wide Unicode characters such as CJK or emoji in titles can misalign the table.
