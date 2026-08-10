# OOTP Schedule Variation Generator

This script generates alternate versions of an OOTP schedule file by reordering teams within divisions and swapping home/away assignments on alternating variants.

## What it does

The script:

- reads an existing `.lsdl` schedule file
- parses the league structure from the filename
- shuffles teams within each division
- writes a new schedule variant for each requested year/variant
- alternates home/away matchups on even-numbered variants

This is useful when you need multiple schedule patterns without manually editing the XML.

## Supported filename format

The script infers team groups by scanning the filename for underscore-separated segments like:

- `T10`
- `T8`
- `T12`

Example:

- `AL_East_T5_T5_T5` 
- `NL_T10_T10_T10_T10`

Each `T#` segment is treated as a division size, and the script groups teams sequentially.

## Requirements

This script uses only Python standard library modules:

- `argparse`
- `xml.etree.ElementTree`
- `random`
- `os`
- `glob`
- `sys`

No external dependencies are required.

## Usage

From the same directory as the script:

```bash
python ootp_schedule_variation.py -i "base_schedule.lsdl" -v 6
```

### Command-line options

- `-i, --input`: path to the base `.lsdl` file
- `-v, --variants`: number of variants to generate (default: `6`)

If `-i` is omitted, the script will:

1. look for `.lsdl` files in the current directory
2. auto-select the only file if there is exactly one
3. prompt the user to choose a file if multiple are present

## Output

The script writes files named like:

```text
<base_name>_v1.lsdl
<base_name>_v2.lsdl
<base_name>_v3.lsdl
```

Each file keeps the original XML structure but rewrites the team mapping for that variant.

## Variant behavior

For each generated variant:

- teams are shuffled within each division
- the mapping is applied to all `GAME` elements in the schedule
- even-numbered variants swap `away` and `home`

This produces different but structurally valid schedule variants while preserving the underlying league layout.

## Example

If the base schedule contains teams `1..12` and the filename indicates divisions of `T6_T6`, the script will:

- treat the first six teams as one division
- treat the next six teams as another division
- shuffle each division independently
- write a new `.lsdl` file for each requested variant

## Notes

- The script relies on the filename being recognizable enough to infer division sizes.
- If the filename does not contain valid `T#` segments, it raises a `ValueError`.
- Output files are written in the current working directory unless you run it from a different folder and path accordingly.

## Example full command

```bash
python ootp_schedule_variation.py -i "../schedule_base.lsdl" -v 12
```

This will generate 12 new schedule files in the working directory.
