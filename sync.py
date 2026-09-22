#!/usr/bin/env python3
"""Refresh data/catalogue.json from the roll index in punch-225.

That working copy is owned by another project and is read, never written. It supplies
what Stanford catalogues about each roll and whether a scan of it exists. What was read
off the rolls is kept in data/readings.json, which this repo owns and nothing here
overwrites.
"""
import json
from pathlib import Path

HERE = Path(__file__).parent
SOURCE = Path("/Users/nielspfeffer/Projects/welte225.org/punch-225/dates/candidates.json")
TARGET = HERE / "data" / "catalogue.json"

ROLL_FIELDS = ("druid", "welte_number", "callnum", "title", "performer")


def trim(roll):
    return {**{f: roll.get(f) for f in ROLL_FIELDS}, "scanned": bool(roll.get("regions"))}


def main():
    if not SOURCE.exists():
        raise SystemExit(f"source not found: {SOURCE}")
    rolls = json.loads(SOURCE.read_text())
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(json.dumps([trim(r) for r in rolls],
                                 ensure_ascii=False, separators=(",", ":")))
    print(f"{len(rolls)} rolls -> {TARGET.relative_to(HERE)} {TARGET.stat().st_size / 1e3:.0f} kB")


if __name__ == "__main__":
    main()
