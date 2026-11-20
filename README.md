# 🌱 aicare

> *I care about AI consumption.*

Every Claude Code session burns tokens, and every token burns some electricity.
**aicare** is a small wrapper around [ccusage](https://github.com/ryoppippi/ccusage). It takes your daily
token report and adds the cost that doesn't show up on the invoice: **kilowatt-hours and kilograms of CO₂**.

## ✨ What you get

- **Daily report** with the usual ccusage columns (tokens, cache, cost), plus:
  - **Session**: the name of each Claude Code session active that day. It uses the name you set with `/rename` or, if there isn't one, the auto-generated title.
  - **Power [kWh]**: estimated energy used.
  - **Footprint [kg]**: estimated CO₂ emitted.
- **Weekly summary** that turns the energy figure into something you can picture: *how many hours a 2 kW
  appliance would have to run to use the same amount.*

## 🚀 Quick start

```bash
./setup.sh          # installs Bun (provides bunx), first-time only
python3 aicare.py
```

The only requirements are Python 3.9+ and `bunx`. The script uses nothing beyond the Python standard library.

## 📊 Example output

Real usage from about a month of daily Claude Code work. The session names are replaced with gibberish to keep them private.

```text
Querying local logs via bunx...

Claude Code Token Usage Report - Daily

┌────────────┬──────────────────────────────────┬──────────────┬───────┬───────────┬──────────────┬─────────────┬──────────────┬────────────┬─────────────┬────────────────┐
│ Date       │ Session                          │ Models       │ Input │ Output    │ Cache Create │ Cache Read  │ Total Tokens │ Cost (USD) │ Power [kWh] │ Footprint [kg] │
├────────────┼──────────────────────────────────┼──────────────┼───────┼───────────┼──────────────┼─────────────┼──────────────┼────────────┼─────────────┼────────────────┤
│ 2026-10-20 │ Mek lomiwex gro loquovo          │ - opus-5-5   │   106 │    37,951 │      251,690 │   5,238,785 │    5,528,532 │      $2.85 │       0.339 │          0.093 │
│            │ Fli mirix                        │ - sonnet-5-5 │       │           │              │             │              │            │             │                │
│            │ Fliloly rix                      │              │       │           │              │             │              │            │             │                │
├────────────┼──────────────────────────────────┼──────────────┼───────┼───────────┼──────────────┼─────────────┼──────────────┼────────────┼─────────────┼────────────────┤
│ 2026-10-21 │ Lymeklo lo                       │ - opus-5-5   │   282 │   128,503 │      570,268 │  20,511,465 │   21,210,518 │      $9.52 │       1.187 │          0.327 │
│            │ Fliber zulydun tanzuly           │              │       │           │              │             │              │            │             │                │
│            │ Zuwex milylo vonapwex            │              │       │           │              │             │              │            │             │                │
├────────────┼──────────────────────────────────┼──────────────┼───────┼───────────┼──────────────┼─────────────┼──────────────┼────────────┼─────────────┼────────────────┤
│ 2026-10-22 │ Torly grodun tan rixmily quonap  │ - opus-5-5   │   702 │   281,172 │    1,393,755 │  54,053,268 │   55,728,897 │     $23.41 │       2.991 │          0.823 │
│            │ Tordunbra zu flitansha nap       │              │       │           │              │             │              │            │             │                │
│            │ Mi lyshasha grobranap tormimi n… │              │       │           │              │             │              │            │             │                │
│            │ Dunlytor mekgro                  │              │       │           │              │             │              │            │             │                │
│    …       │ …                                │  …           │     … │         … │            … │           … │            … │          … │           … │              … │
├────────────┼──────────────────────────────────┼──────────────┼───────┼───────────┼──────────────┼─────────────┼──────────────┼────────────┼─────────────┼────────────────┤
│ Total      │                                  │              │ 9,346 │ 3,703,701 │   21,539,319 │ 810,721,803 │  835,974,169 │    $398.51 │      44.012 │         12.103 │
└────────────┴──────────────────────────────────┴──────────────┴───────┴───────────┴──────────────┴─────────────┴──────────────┴────────────┴─────────────┴────────────────┘

You have spent the equivalent hours of a 2000 [W] electric load during these weeks:
┌───────┬─────────────────────┐
│ Week  │ Equivalent load [h] │
├───────┼─────────────────────┤
│    43 │                3.44 │
├───────┼─────────────────────┤
│    44 │                2.75 │
├───────┼─────────────────────┤
│    45 │                4.95 │
├───────┼─────────────────────┤
│    46 │                4.52 │
├───────┼─────────────────────┤
│    47 │                6.35 │
├───────┼─────────────────────┤
│ Total │               22.01 │
└───────┴─────────────────────┘
```

So a month of AI-assisted coding came to about **44 kWh** and **12 kg of CO₂**. That's roughly a 2 kW electric
heater running for **22 hours**.

## ⚙️ Configuration

| Environment variable                    | Default | Meaning                                                         |
|-----------------------------------------|---------|-----------------------------------------------------------------|
| `AICARE_ANTHROPIC_WH_PER_1M_OUTPUT`     | `1950`  | Wh per 1M output tokens                                         |
| `AICARE_ANTHROPIC_WH_PER_1M_INPUT`      | `240`   | Wh per 1M input and cache-creation tokens                       |
| `AICARE_ANTHROPIC_WH_PER_1M_CACHE_READ` | `39`    | Wh per 1M cache-read tokens                                     |
| `AICARE_GRID_KG_CO2_PER_KWH`            | `0.275` | Grid carbon intensity, kg CO₂ per kWh                           |
| `AICARE_EXAMPLE_ELECTRIC_LOAD`          | `2000`  | Reference load in watts for the weekly "equivalent hours" table |

If a value is missing, not a number, or negative, aicare uses the default. The electric load must also be greater than zero.
The last line of the output lists every setting, its value, and whether it came from the environment or the default.

```bash
AICARE_EXAMPLE_ELECTRIC_LOAD=60 python3 aicare.py   # in hours of an old 60 W light bulb
AICARE_GRID_KG_CO2_PER_KWH=0.05 python3 aicare.py  # if your grid is mostly hydro/nuclear
```

## 🔬 How the numbers are estimated

aicare multiplies token counts by per-token energy factors, then by a grid carbon intensity:

| Token type                 | Energy per 1M tokens |
|----------------------------|----------------------|
| Output                     | 1950 Wh              |
| Input + cache creation     | 240 Wh               |
| Cache read                 | 39 Wh                |

| Grid      | Carbon intensity     |
|-----------|----------------------|
| Italy 🇮🇹 | 0.275 kg CO₂ / kWh   |

These are **order-of-magnitude estimates**, not measurements. Anthropic doesn't publish per-token energy
figures, so take the results as a way to raise awareness, not as an audit. You can change every factor with
an environment variable (see [Configuration](#️-configuration)) to match your own assumptions or your local grid.

Weeks start on Monday and use ISO week numbers.

## 🧭 Caveats

- Energy and cost are calculated **per day**. The Session column only lists which sessions were active; it doesn't split the totals between them.
- Session names come from Claude Code's internal transcript format (`~/.claude/projects/**/*.jsonl`), which is undocumented and may change.

## 🙏 Credits

Token accounting by [ccusage](https://github.com/ryoppippi/ccusage). Guilt by aicare.
