#!/usr/bin/env python3
"""Refresh data/rolls.source.json from the dating run in punch-225.

That working copy is owned by another project and is read, never written. Run this
when it re-emits candidates.json; build.py works only from the copy written here, so
a clone of this repo rebuilds the site without needing punch-225 at all.

Carried over: one record per roll with the fields the site uses, and for each region
the geometry of its view boxes. Left behind: the region scoring, and the reading,
confidence and per-roll notes, which are the argument rather than the overview and
stay in punch-225.

A region's rotation lives only inside its IIIF URL, so it is parsed out here and
stored beside the box rather than assumed. Every region in the present run reads 90,
but nothing guarantees that. Parsing it is the one thing this script decides;
everything else it copies.
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).parent
SOURCE = Path("/Users/nielspfeffer/Projects/welte225.org/punch-225/dates/candidates.json")
TARGET = HERE / "data" / "rolls.source.json"

ROLL_FIELDS = ("druid", "welte_number", "callnum", "title", "performer",
               "date_iso", "inscription", "hand", "read_region")
ROTATION = re.compile(r"/(\d+)/default\.jpg$")


def geometry(view):
    rotation = ROTATION.search(view.get("url") or "")
    if not rotation or not all(f in view for f in "xywh"):
        return None
    return {"box": f"{view['x']},{view['y']},{view['w']},{view['h']}",
            "rot": int(rotation[1])}


def views(region):
    """Every view variant of a region, as a IIIF box and rotation.

    read_region is 1-based into this array in the order the file lists it, so the
    array keeps its length and order even where a region carries no view at all.
    """
    return {key: box for key, view in region.items()
            if key.startswith("view") and isinstance(view, dict)
            for box in [geometry(view)] if box}


def trim(roll):
    record = {f: roll.get(f) for f in ROLL_FIELDS}
    record["regions"] = [views(r) for r in roll.get("regions") or []]
    return record


def main():
    if not SOURCE.exists():
        raise SystemExit(f"source not found: {SOURCE}")
    rolls = json.loads(SOURCE.read_text())
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(json.dumps([trim(r) for r in rolls],
                                 ensure_ascii=False, separators=(",", ":")))
    print(f"{len(rolls)} rolls  {SOURCE.stat().st_size / 1e6:.2f} MB "
          f"-> {TARGET.relative_to(HERE)} {TARGET.stat().st_size / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
