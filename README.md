# OOTP

This folder contains scripts and utilities related to OOTP baseball league operations, schedule generation, and league data processing.

## Table of Contents

- [ScheduleGenerator](#schedulegenerator)

---

<h2><u>Scripts</u></h2>

### ScheduleGenerator

Generates custom OOTP Baseball schedule XML files for leagues with multiple subleagues, divisions, and teams. The script supports balanced home/away splits, mixed-length series, optional interleague play, and dynamic All-Star Game placement.

**Prerequisites:**
- Python 3
- No additional dependencies required

**Features:**
- Multiple subleagues and divisions
- Configurable teams per division
- Adjustable games per team
- Mixed 2-game, 3-game, and 4-game series support
- Optional interleague play
- XML output compatible with OOTP `.lsdl` schedule imports
- Dynamic All-Star Game scheduling based on day or weekday constraints

**Usage:**

```bash
cd ScheduleGenerator
python ootp_schedule_generator.py \
  -s 2 \
  -d 2 \
  -t 4 \
  -g 162 \
  --non-interactive
```

**Notes:**
- Run the script interactively to choose from valid schedule distribution options.
- Use `--non-interactive` to automatically select the top valid option.
- Use `-a` or `-aw` to position the All-Star break around a target day or weekday.

---

This section will expand as additional OOTP scripts are added and finalized.
