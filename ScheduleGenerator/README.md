# OOTP Schedule Generator

This script generates custom OOTP baseball schedule files in XML format for leagues with multiple subleagues, divisions, and teams. It supports balanced intra-division scheduling, mixed-length series, optional interleague play, and dynamic All-Star Game placement.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Features](#features)
- [Usage](#usage)
- [Command-Line Parameters](#command-line-parameters)
- [Interactive Schedule Breakdown Selection](#interactive-schedule-breakdown-selection)
- [Game Distribution Logic](#game-distribution-logic)
- [All-Star Game Placement](#all-star-game-placement)
- [Output](#output)
- [Notes](#notes)

---

<h2><u>Script</u></h2>

### ootp_schedule_generator.py

Generates a full season schedule for an OOTP league, including home/away balancing, mixed series lengths, and calendar spacing to produce a realistic season structure. The output is intended for use as an OOTP `.lsdl` schedule file.

**Prerequisites:**
- Python 3
- No external dependencies required

**Features:**
- Multiple subleagues and divisions
- Configurable team counts per division
- Adjustable games per team
- Support for mixed 2-game, 3-game, and 4-game series
- Optional interleague play
- Auto or interactive valid distribution selection
- XML output compatible with OOTP schedule imports
- Dynamic All-Star Game placement based on date or weekday constraints

**Usage:**

```bash
python ootp_schedule_generator.py \
  -s 2 \
  -d 2 \
  -t 4 \
  -g 162 \
  -il 1 \
  --non-interactive
```

This creates a schedule for:
- 2 subleagues
- 2 divisions per subleague
- 4 teams per division
- 162 games per team
- interleague play enabled
- automatic selection of the top valid schedule breakdown

**Command-Line Parameters:**
- `-s, --subleagues`: Number of subleagues in the league.
- `-d, --divisions`: Number of divisions in each subleague.
- `-t, --teams-per-div`: Number of teams in each division.
- `-g, --games`: Total games per team for the season.
- `-il, --interleague`: Enable or disable interleague play (`0` or `1`).
- `-bg, --balanced`: Toggle balanced scheduling behavior (`0` or `1`).
- `-a, --allstar-game-day`: Target calendar day for the All-Star Game.
- `-aw, --asg-weekday`: Force the All-Star Game to a specific weekday such as `Thursday`.
- `-ab, --asg-before`: Number of days to reserve before the break.
- `-aa, --asg-after`: Number of days to reserve after the break.
- `-sdw, --start-day-of-week`: Day of the week the schedule should begin on.
- `-sm, --start-month`: Month the schedule should begin in.
- `-sd, --start-day`: Day of the month the schedule should begin on.
- `-o, --output`: Custom output filename for the generated XML.
- `--non-interactive`: Skip the breakdown prompt and automatically choose the first valid option.

**Interactive Schedule Breakdown Selection:**

When the script runs in interactive mode, it displays all valid schedule breakdown combinations and prompts the user to choose the option that best fits the league setup.

![Interactive schedule breakdown selection](./schedule_breakdown_selection.png)

This prompt shows the available distribution options, the selected choice, and the generated season summary after the schedule is created.

**Game Distribution Logic:**

The script validates possible game distributions before generating the schedule. It looks for combinations that match the league structure and the total number of games, then presents the valid options to the user. These can include:
- all 3-game series
- mixed 3-game and 4-game series
- mixed 2-game and 3-game series

The generator prefers valid configurations that maintain a balanced home/away split and realistic series spacing.

**All-Star Game Placement:**

When `-a` or `-aw` is provided, the script attempts to place the All-Star break in a realistic calendar position while preserving the season structure. This is especially useful when the schedule must align with a target weekday or date.

Example:

```bash
python ootp_schedule_generator.py \
  -s 2 -d 2 -t 4 -g 162 \
  -a 105 \
  -aw Thursday \
  -ab 3 \
  -aa 3 \
  -sdw Friday \
  -sm April \
  -sd 1
```

This places the All-Star Game near calendar day 105 while respecting the requested weekday and spacing around the break.

**Output:**

The script writes an XML schedule file to the current directory by default, using names such as:

```text
ILY_BGN_G162_SL1_D2_T4_SL2_D2_T4.lsdl
```

The file contains a root `SCHEDULE` element with attributes including:
- `type`
- `inter_league`
- `balanced_games`
- `games_per_team`
- `start_day_of_week`
- `start_month`
- `start_day`

Each game is written as a `<GAME>` element with:
- `day`
- `time`
- `away`
- `home`

**Notes:**
- If the script is run in an interactive terminal, it asks the user to select a valid game distribution.
- If `stdin` is not a TTY or `--non-interactive` is passed, it automatically chooses the first valid distribution.
- The schedule format is intended for OOTP import and is not a general baseball scheduling library.

---

This script is designed for personal and league-use scheduling work. It is provided as-is and can be adapted to fit a specific league format or custom OOTP setup.
