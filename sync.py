#!/usr/bin/env python3
"""Refresh data/catalogue.json and data/perforator.json from punch-225.

    python3 sync.py [punch-225/dates]

That working copy is owned by another project and is read, never written. It supplies
what Stanford catalogues about each roll, whether a scan of it exists and where in it the
paper lies (its first and last columns, its length, and the rows of its first and last
hole), and the two sweeps that measured the perforator on
every scan: pitch.json (chain pitch, slot, bridge, Teilung, the parser's hole width) and
step.json (the advance). The scripts that take those measurements stay in punch-225; this
repo keeps and publishes their results, together with the commit of welte225.org they were
synced at, so that a record can link the script that measured it. What was read off the
rolls is kept in data/readings.json, which this repo owns and nothing here overwrites.
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
SOURCE = Path("/Users/nielspfeffer/Projects/welte225.org/punch-225/dates")
CATALOGUE = HERE / "data" / "catalogue.json"
PERFORATOR = HERE / "data" / "perforator.json"

ROLL_FIELDS = ("druid", "welte_number", "callnum", "title", "performer")


def trim(roll):
    return {**{f: roll.get(f) for f in ROLL_FIELDS}, "scanned": bool(roll.get("regions")),
            "paper": roll.get("paper_columns"), "length": roll.get("image_length"),
            "holes": [roll.get("first_hole"), roll.get("last_hole")]}


def keyed(rows):
    """A sweep's rows by druid, without the druid; a row that measured nothing is left out."""
    return {row["druid"]: {k: v for k, v in row.items() if k != "druid"}
            for row in rows if row.get("n")}


def commit(source):
    """The commit the working copy stands at, or None where it is not a git checkout."""
    found = subprocess.run(["git", "-C", str(source), "rev-parse", "HEAD"], capture_output=True, text=True)
    return found.stdout.strip() or None


def write(target, data):
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    print(f"-> {target.relative_to(HERE)} {target.stat().st_size / 1e3:.0f} kB")


def main():
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else SOURCE
    paths = [source / name for name in ("candidates.json", "pitch.json", "step.json")]
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        raise SystemExit(f"source not found: {', '.join(missing)}")
    rolls, pitch, step = (json.loads(p.read_text()) for p in paths)

    write(CATALOGUE, [trim(r) for r in rolls])
    pitch, step = keyed(pitch), keyed(step)
    write(PERFORATOR, {
        "commit": commit(source),
        "rolls": {druid: {k: v for k, v in (("pitch", pitch.get(druid)), ("step", step.get(druid))) if v}
                  for druid in sorted(pitch.keys() | step.keys())},
    })
    print(f"{len(rolls)} rolls, {len(pitch)} with a pitch, {len(step)} with an advance")


if __name__ == "__main__":
    main()
