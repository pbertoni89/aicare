#!/usr/bin/env python3

import subprocess
import re

# Energy parameters for high-density models (e.g. Opus/Sonnet 3.5)
WH_PER_1M_OUTPUT = 1950.0
WH_PER_1M_CACHE_READ = 39.0
WH_PER_1M_INPUT = 240.0
KG_CO2_PER_KWH_ITALY = 0.275

def parse_int(text_val: str) -> int:
    """
    Extract numeric value from a string by removing spaces and commas.
    """
    cleaned = re.sub(r'[^\d]', '', text_val)
    return int(cleaned) if cleaned else 0

def calculate_metrics(tokens_input: int, tokens_output: int,
                      tokens_ccreate: int, tokens_cread: int) -> tuple[float, float]:
    """
    Calculate power usage (kWh) and carbon footprint (kg CO2) based on token counts.
    """
    wh_output = (tokens_output / 1_000_000) * WH_PER_1M_OUTPUT
    wh_cache_read = (tokens_cread / 1_000_000) * WH_PER_1M_CACHE_READ
    wh_input = ((tokens_input + tokens_ccreate) / 1_000_000) * WH_PER_1M_INPUT

    power_kwh = (wh_output + wh_cache_read + wh_input) / 1000.0
    co2_kg = power_kwh * KG_CO2_PER_KWH_ITALY

    return power_kwh, co2_kg

def enrich_table_line(raw_line: str) -> str:
    """
    Parse a single line of the ccusage output table and append Power and CO2 columns.
    Maintains the original ASCII table formatting.
    """
    line = raw_line.rstrip('\n\r ')

    if not line:
        return raw_line

    # Handle table borders
    if line.endswith('┐'):
        return line[:-1] + "┬" + "─"*13 + "┬" + "─"*16 + "┐"
    elif line.endswith('┤'):
        return line[:-1] + "┼" + "─"*13 + "┼" + "─"*16 + "┤"
    elif line.endswith('┘'):
        return line[:-1] + "┴" + "─"*13 + "┴" + "─"*16 + "┘"

    # Handle table rows
    elif line.endswith('│'):
        # Header row detection
        if ' Date ' in line and ' Models ' in line:
            return line[:-1] + f"│ {'Power [kWh]'.center(11)} │ {'Footprint [kg]'.center(14)} │"

        # Data row parsing
        parts = line.split('│')
        if len(parts) >= 9:
            col_date = parts[1].strip()
            col_input = parts[3].strip()
            col_output = parts[4].strip()
            col_ccreate = parts[5].strip()
            col_cread = parts[6].strip()

            # Check if this row actually contains the aggregated data (Date or Total row)
            is_valid_row = bool(re.match(r'\d{4}-\d{2}-\d{2}', col_date)) or col_date.lower() == 'total'

            if is_valid_row and col_input:
                try:
                    tokens_input = parse_int(col_input)
                    tokens_output = parse_int(col_output)
                    tokens_ccreate = parse_int(col_ccreate)
                    tokens_cread = parse_int(col_cread)

                    power_kwh, co2_kg = calculate_metrics(
                        tokens_input, tokens_output, tokens_ccreate, tokens_cread
                    )
                    return line[:-1] + f"│ {power_kwh:>11.3f} │ {co2_kg:>14.3f} │"
                except ValueError:
                    pass

        # Sub-rows (e.g., additional models on the same day without token totals)
        return line[:-1] + f"│ {' '*11} │ {' '*14} │"

    return raw_line

def main():
    """
    Execute bunx ccusage, capture the output, and print the enriched table.
    """
    print("Querying local logs via bunx...\n")

    try:
        result = subprocess.run(
            ["bunx", "ccusage", "claude", "daily"],
            capture_output=True, text=True, check=True
        )
        output = result.stdout
    except Exception as e:
        print(f"Error executing ccusage: {e}")
        return

    # Process and print the CLI output line by line
    for line in output.splitlines():
        if '│' in line or '┐' in line or '┤' in line or '┘' in line:
            print(enrich_table_line(line))
        else:
            print(line)

if __name__ == '__main__':
    main()
