# OOTP Schedule Generator

This script generates a custom OOTP Baseball schedule in XML format for a league structure with multiple subleagues, divisions, and teams. It is built to support balanced intra-division schedules, mixed-length series, optional interleague play, and a dynamic All-Star Game placement.

The output is intended for use as an OOTP `.lsdl` schedule file.

## Overview

The generator:

- builds a round-robin structure for each division
- creates cross-division and interleague pairings
- distributes games into series lengths such as 2-game, 3-game, and 4-game series
- balances home/away splits
- slots games across the calendar to produce a realistic season layout
- optionally forces an All-Star break on a target calendar day or weekday

## Features

- Supports multiple subleagues and divisions
- Configurable teams per division
- Adjustable total games per team
- Optional interleague play
- Mixed-series scheduling (not limited to pure 3-game blocks)
- Interactive breakdown selection by default, or automated selection with `--non-interactive`
- XML output compatible with OOTP schedule imports
- All-Star Game placement logic with before/after break windows

## Script

- Main script: `ootp_schedule_generator.py`

## Quick Start

Run the script with inputs for the league setup you want:

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

## Command-Line Options

```bash
usage: ootp_schedule_generator.py [-h]
  -s --subleagues
  -d --divisions
  -t --teams-per-div
  -g --games
  -il --interleague {0,1}
  -bg --balanced {0,1}
  -a --allstar-game-day
  -aw --asg-weekday
  -ab --asg-before
  -aa --asg-after
  -sdw --start-day-of-week
  -sm --start-month
  -sd --start-day
  -o --output
  --non-interactive
```

### Important arguments

- `-s, --subleagues`: number of subleagues
- `-d, --divisions`: number of divisions in each subleague
- `-t, --teams-per-div`: team count in each division
- `-g, --games`: games per team in the season
- `-il, --interleague`: enable or disable interleague games
- `-a, --allstar-game-day`: target calendar day for the All-Star Game
- `-aw, --asg-weekday`: force the All-Star Game to a specific weekday such as `Thursday`
- `-ab, --asg-before`: days before the break to reserve
- `-aa, --asg-after`: days after the break to reserve
- `-sdw, --start-day-of-week`: day the schedule should begin on (for example Monday or Friday)
- `-sm, --start-month`: month of the first scheduled day
- `-sd, --start-day`: day of the month for the first scheduled game
- `-o, --output`: custom output filename
- `--non-interactive`: skip the breakdown prompt and choose the top valid option automatically

## Game Distribution Logic

The script validates possible game distributions before generating the schedule. It looks for combinations that match the league structure and the total number of games. These are then displayed as schedule options, for example:

- all 3-game series
- mixed 3-game and 4-game series
- mixed 2-game and 3-game series

The script prefers valid configurations that preserve balanced home/away totals and can present several possible options to the user.

## All-Star Game Placement

When `-a` or `-aw` is provided, the script tries to position an All-Star break in the calendar while keeping the season structure coherent. This is especially useful when the schedule must line up with a specific weekday or day number.

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

This places the All-Star Game on or near calendar day 105, adjusted to the requested weekday while respecting the before/after break spacing.

## Output File

The script writes an XML schedule file to the current directory by default, using names such as:

```text
ILY_BGN_G162_SL1_D2_T4_SL2_D2_T4.lsdl
```

The file contains a root `SCHEDULE` element with attributes like:

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

## Notes

- If run in an interactive terminal, the script asks the user to select a valid game distribution.
- If `stdin` is not a TTY or `--non-interactive` is passed, it automatically chooses the first valid distribution.
- The schedule format is intended for OOTP import and is not a general baseball scheduling library.

## Example Output Summary

When complete, the script prints a summary like:

```text
Generated 3240 total games across 16 teams.
All-Star Game scheduled dynamically for Day 105 (Thursday)
File saved to: ILY_BGN_G162_SL1_D2_T4_SL2_D2_T4.lsdl
```

## License

This project is provided as-is for personal or league-use scheduling work. If you are using it outside your own environment, confirm any license or usage requirements associated with your broader project.
