#!/usr/bin/env python3

import glob
import json
import os
import subprocess
from collections import defaultdict
from datetime import date, datetime


# Every setting resolved by env_float(): {name: (value, source)}, reported at exit
ENV_SETTINGS: dict[str, tuple[float, str]] = {}


def env_float(name: str, default: float, allow_zero: bool = True) -> float:
    """
    Read a numeric env var. Falls back to default if unset, not a number, negative
    (or zero, when allow_zero is False). Records the outcome in ENV_SETTINGS.
    """
    raw = os.environ.get(name)
    if raw is None:
        ENV_SETTINGS[name] = (default, "default")
        return default
    try:
        value = float(raw)
    except ValueError:
        value = None
    if value is None or value < 0 or (value == 0 and not allow_zero):
        ENV_SETTINGS[name] = (default, f"default, ignored invalid {raw!r}")
        return default
    ENV_SETTINGS[name] = (value, "env")
    return value


def format_env_settings() -> str:
    return "\n\t".join(f"{name} = {value:g} ({source})"
                       for name, (value, source) in ENV_SETTINGS.items())


# Energy estimates for Anthropic's high-density models, in Wh per 1M tokens
WH_PER_1M_OUTPUT = env_float("AICARE_ANTHROPIC_WH_PER_1M_OUTPUT", 1950.0)
WH_PER_1M_CACHE_READ = env_float("AICARE_ANTHROPIC_WH_PER_1M_CACHE_READ", 39.0)
WH_PER_1M_INPUT = env_float("AICARE_ANTHROPIC_WH_PER_1M_INPUT", 240.0)  # also used for cache creation
# Grid carbon intensity
KG_CO2_PER_KWH = env_float("AICARE_GRID_KG_CO2_PER_KWH", 0.275)

# Directories where Claude Code stores session transcripts (same ones ccusage reads)
CLAUDE_PROJECT_DIRS = [
    os.path.expanduser("~/.claude/projects"),
    os.path.expanduser("~/.config/claude/projects"),
]
SESSION_TITLE_MAX = 32
DEFAULT_EXAMPLE_LOAD_W = 2000.0


def calculate_metrics(tokens_input: int, tokens_output: int,
                      tokens_ccreate: int, tokens_cread: int) -> tuple[float, float]:
    """
    Calculate power usage (kWh) and carbon footprint (kg CO2) based on token counts.
    """
    wh_output = (tokens_output / 1_000_000) * WH_PER_1M_OUTPUT
    wh_cache_read = (tokens_cread / 1_000_000) * WH_PER_1M_CACHE_READ
    wh_input = ((tokens_input + tokens_ccreate) / 1_000_000) * WH_PER_1M_INPUT

    power_kwh = (wh_output + wh_cache_read + wh_input) / 1000.0
    co2_kg = power_kwh * KG_CO2_PER_KWH

    return power_kwh, co2_kg


def truncate(text: str, width: int) -> str:
    return text if len(text) <= width else text[:width - 1] + "…"


def load_sessions_by_date() -> dict[str, list[str]]:
    """
    Scan Claude Code JSONL transcripts and return {local date: [session titles]}.
    A session counts for a date if it produced at least one assistant message that day.
    Title preference: custom-title (/rename) > ai-title > short session id.
    """
    custom_titles: dict[str, str] = {}
    ai_titles: dict[str, str] = {}
    dates_by_session: dict[str, set[str]] = defaultdict(set)
    first_seen: dict[str, str] = {}

    files = []
    for base in CLAUDE_PROJECT_DIRS:
        files += glob.glob(os.path.join(base, "**", "*.jsonl"), recursive=True)

    for path in files:
        try:
            fh = open(path, encoding="utf-8", errors="replace")
        except OSError:
            continue
        with fh:
            for line in fh:
                # Cheap substring filter before paying for json.loads
                if ('"type":"assistant"' not in line and '"custom-title"' not in line
                        and '"ai-title"' not in line):
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                sid = rec.get("sessionId")
                if not sid:
                    continue
                kind = rec.get("type")
                if kind == "custom-title" and rec.get("customTitle"):
                    custom_titles[sid] = rec["customTitle"]
                elif kind == "ai-title" and rec.get("aiTitle"):
                    ai_titles[sid] = rec["aiTitle"]
                elif kind == "assistant" and rec.get("timestamp"):
                    try:
                        ts = datetime.fromisoformat(rec["timestamp"].replace("Z", "+00:00"))
                    except ValueError:
                        continue
                    day = ts.astimezone().date().isoformat()
                    dates_by_session[sid].add(day)
                    if sid not in first_seen or rec["timestamp"] < first_seen[sid]:
                        first_seen[sid] = rec["timestamp"]

    by_date: dict[str, list[str]] = defaultdict(list)
    for sid in sorted(dates_by_session, key=lambda s: first_seen[s]):
        title = custom_titles.get(sid) or ai_titles.get(sid) or sid[:8]
        title = truncate(title, SESSION_TITLE_MAX)
        for day in dates_by_session[sid]:
            # Forked/continued sessions often share a title: list it once per day
            if title not in by_date[day]:
                by_date[day].append(title)
    return by_date


def render_table(headers: list[str], aligns: list[str], rows: list[list[list[str]]]) -> str:
    """
    Render a box-drawing table. Each cell is a list of lines (multi-line cells allowed).
    aligns: 'l' or 'r' per column.
    """
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            for text in cell:
                widths[i] = max(widths[i], len(text))

    def border(left: str, mid: str, right: str) -> str:
        return left + mid.join("─" * (w + 2) for w in widths) + right

    def fmt_row(cells: list[list[str]], force_left: bool = False) -> list[str]:
        height = max(len(c) for c in cells)
        out = []
        for n in range(height):
            parts = []
            for i, cell in enumerate(cells):
                text = cell[n] if n < len(cell) else ""
                if aligns[i] == "r" and not force_left:
                    parts.append(f" {text:>{widths[i]}} ")
                else:
                    parts.append(f" {text:<{widths[i]}} ")
            out.append("│" + "│".join(parts) + "│")
        return out

    lines = [border("┌", "┬", "┐")]
    lines += fmt_row([[h] for h in headers], force_left=True)
    for row in rows:
        lines.append(border("├", "┼", "┤"))
        lines += fmt_row(row)
    lines.append(border("└", "┴", "┘"))
    return "\n".join(lines)


def build_row(label: str, sessions: list[str], models: list[str], entry: dict) -> list[list[str]]:
    power_kwh, co2_kg = calculate_metrics(
        entry["inputTokens"], entry["outputTokens"],
        entry["cacheCreationTokens"], entry["cacheReadTokens"],
    )
    return [
        [label],
        sessions or [""],
        models or [""],
        [f"{entry['inputTokens']:,}"],
        [f"{entry['outputTokens']:,}"],
        [f"{entry['cacheCreationTokens']:,}"],
        [f"{entry['cacheReadTokens']:,}"],
        [f"{entry['totalTokens']:,}"],
        [f"${entry['totalCost']:,.2f}"],
        [f"{power_kwh:.3f}"],
        [f"{co2_kg:.3f}"],
    ]


def main():
    """
    Execute bunx ccusage (JSON mode), add session names, power and CO2, print the table.
    """
    print("Querying local logs via bunx...\n")

    try:
        result = subprocess.run(
            ["bunx", "ccusage", "claude", "daily", "--json"],
            capture_output=True, text=True, check=True
        )
        report = json.loads(result.stdout)
    except Exception as e:
        print(f"Error executing ccusage: {e}")
        return

    sessions_by_date = load_sessions_by_date()

    rows = []
    for day in report.get("daily", []):
        models = [f"- {m.removeprefix('claude-')}" for m in day.get("modelsUsed", [])]
        rows.append(build_row(day["date"], sessions_by_date.get(day["date"], []), models, day))
    rows.append(build_row("Total", [], [], report["totals"]))

    headers = ["Date", "Session", "Models", "Input", "Output", "Cache Create",
               "Cache Read", "Total Tokens", "Cost (USD)", "Power [kWh]", "Footprint [kg]"]
    aligns = ["l", "l", "l", "r", "r", "r", "r", "r", "r", "r", "r"]

    print("Claude Code Token Usage Report - Daily\n")
    print(render_table(headers, aligns, rows))

    print_weekly_load(report.get("daily", []))

    print(f"\nSettings used:\n\t{format_env_settings()}")


def get_example_load_watts() -> float:
    """
    Read AICARE_EXAMPLE_ELECTRIC_LOAD [W] from the environment, falling back to the default.
    """
    return env_float("AICARE_EXAMPLE_ELECTRIC_LOAD", DEFAULT_EXAMPLE_LOAD_W, allow_zero=False)


def print_weekly_load(daily: list[dict]) -> None:
    """
    Group daily energy by ISO week (Monday start) and express it as hours of a reference load.
    """
    watts = get_example_load_watts()
    kwh_by_week: dict[tuple[int, int], float] = defaultdict(float)
    for day in daily:
        year, week, _ = date.fromisoformat(day["date"]).isocalendar()
        power_kwh, _ = calculate_metrics(
            day["inputTokens"], day["outputTokens"],
            day["cacheCreationTokens"], day["cacheReadTokens"],
        )
        kwh_by_week[(year, week)] += power_kwh

    hours = {key: kwh * 1000.0 / watts for key, kwh in kwh_by_week.items()}
    rows = [[[str(week)], [f"{h:.2f}"]] for (_, week), h in sorted(hours.items())]
    rows.append([["Total"], [f"{sum(hours.values()):.2f}"]])

    print(f"\nYou have spent the equivalent hours of a {watts:g} [W] electric load "
          f"during these weeks:")
    print(render_table(["Week", "Equivalent load [h]"], ["r", "r"], rows))


if __name__ == '__main__':
    main()
