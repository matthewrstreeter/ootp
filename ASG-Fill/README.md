# OOTP All-Star Ballot Filler

This script fills an OOTP All-Star ballot template from a votes export and writes the final team selection text for a league using either of the two common OOTP roster layouts:

- LF/CF/RF + DH
- 3 OF + no DH

It was developed for the AFBL and NPBL formats used in this project, but the profile logic is general enough to support other leagues with either configuration. The league name is used to auto-detect the correct roster shape, and additional league profiles can be added by editing the configuration in the script.

It automatically:

- detects the roster shape from the league in the vote export
- selects the top vote-getter(s) as starters
- picks reserve players based on vote totals
- prompts for manual tie-breaking when vote totals are tied at a cutoff
- optionally shows season stats from StatsPlus to help break ties

## Files

- `ASG-Fill.py` — main script
- `votes.json` — vote export from StatsPlus /votes API

## Requirements

- Python 3
- `requests` package

Install dependencies:

```bash
pip install requests
```

## Usage

```bash
python ASG-Fill.py path/to/votes.json
```

Optional flags:

```bash
python ASG-Fill.py path/to/votes.json -o output.txt
python ASG-Fill.py path/to/votes.json --token YOUR_STATSPLUS_TOKEN
python ASG-Fill.py path/to/votes.json --auto
python ASG-Fill.py path/to/votes.json --no-stats
```

## Environment variable

If you have a StatsPlus token, you can set it once instead of passing it each time:

```bash
export STATSPLUS_API_KEY="YOUR_TOKEN"
```

Then run:

```bash
python ASG-Fill.py path/to/votes.json
```

## What it does

For each league in the vote export, the script:

1. reads the sorted vote totals for each position
2. fills starter slots from the highest-vote candidates
3. resolves tie-breaks at starter cutoffs by prompting the user
4. fills reserve slots while enforcing the reserve vote minimum
5. writes the final selections to a text file such as `AFBL-ASG-2025.txt`

## Sample vote export

The script expects a JSON file with the same general structure as the OOTP votes export. Each result entry includes a year, league, sub-league, position, ballots, and a list of players sorted by vote count. A simplified example:

```json
{
  "results": [
    {
      "year": 2025,
      "league": "AFBL",
      "sub_league": "North",
      "position": "C",
      "ballots": 30,
      "players": [
        {
          "name": "Mason Ellis",
          "teams": "BUF",
          "votes": 28,
          "player_id": "12345"
        },
        {
          "name": "Tony Ruiz",
          "teams": "OKC",
          "votes": 22,
          "player_id": "67890"
        }
      ]
    }
  ]
}
```

The script reads all result entries and groups them by league and position automatically. The `league` field is what determines whether the AFBL or NPBL lineup format is used.

## Example run

```bash
python ASG-Fill.py /path/to/votes.json --token YOUR_STATSPLUS_TOKEN
```

This reads the vote export, resolves starters and reserves for each league in the file, and writes one output text file per league. By default, the file is named like:

```text
AFBL-ASG-2025.txt
NPBL-ASG-2025.txt
```

You can override that with `-o` if you want a custom filename.

## Output format

The script writes a plain-text All-Star ballot summary for the selected league. Example structure:

```text
*2025 All-Star Game Selections*
*AFBL*
_Starters_
CA: Name (TEAM)
1B: Name (TEAM)
...

_Reserves_
CA: Name (TEAM)
...
```

## Tie handling

When a tie occurs around the cutoff:

- the script prompts for a manual pick unless `--auto` is used
- with a valid StatsPlus token, it can display player season stats to inform the decision
- if a reserve slot cannot be filled under the minimum vote threshold, the script notes that manual review is needed

## Sample output

```text
*2025 All-Star Game Selections*
*AFBL*
_Starters_
CA: Mason Ellis (BUF)
1B: Alex Romero (SAC)
2B: Jordan Lee (PHX)
3B: Norman Price (AUS)
SS: Luis Gomez (MON)
LF: Austin Hall (SEA)
CF: Victor Brooks (TOR)
RF: Daniel Shaw (LAD)
DH: Charlie Nguyen (MIL)
SP: Ethan Ross (NYY)

_Reserves_
CA: Tony Ruiz (OKC)
1B: Andre Wells (BOS)
2B: Noah Kim (TEX)
3B: Tomás Silva (HOU)
SS: Isaiah Bell (BAL)
LF: Marcus Frost (CIN)
CF: Brandon Cole (MIA)
RF: Sean Parker (ATL)
SP: Malik James (DET)
SP: Tyler Brooks (KC)
SP: Aiden Moore (WSH)
SP: Omar Hassan (TB)
SP: Kevin Ross (MIN)
RP: Jake Foster (PHI)
RP: David Watts (SD)
RP: Cameron Young (ARI)
RP: Ryan Doyle (SF)
RP: Ethan Ortiz (LAA)
RP: Leo Martin (CLE)
```

## Troubleshooting

- If the script throws a `ModuleNotFoundError` for `requests`, install it with `pip install requests`.
- If the script says there is no StatsPlus token, either set `STATSPLUS_API_KEY` or pass `--token YOUR_TOKEN`.
- If the JSON is malformed, confirm the file is a valid OOTP export and that each result entry includes `year`, `league`, `sub_league`, `position`, `ballots`, and `players`.
- If a position is missing from the output, check whether the league uses a different roster format or whether that position was absent from the export.
- If you do not want to be prompted during tied cutoffs, run with `--auto` to auto-pick the first tied player.

## Notes

- The script supports both common OOTP roster layouts: LF/CF/RF + DH and 3 OF + no DH.
- AFBL and NPBL are built-in example profiles for this project, but the same logic can be reused for other leagues.
- The output path defaults to `<league>-ASG-<year>.txt` in the current directory unless `-o` is specified.
- If no StatsPlus token is available, the script still works, but tie prompts will not show stat comparisons.
