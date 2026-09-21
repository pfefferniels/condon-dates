#!/usr/bin/env python3
"""Regenerate docs/data/rolls.json from the roll data and the signature clustering.

Both inputs live in this repo, so a clone rebuilds the site on its own. Refresh
data/rolls.source.json with sync.py when the dating run re-emits candidates.json.
"""
import html
import json
import re
from datetime import date
from pathlib import Path

HERE = Path(__file__).parent
SOURCE = HERE / "data" / "rolls.source.json"
HANDS = HERE / "hands.json"
TARGET = HERE / "docs" / "data" / "rolls.json"


def read_region(roll):
    """The region the date was read from, with the view variant the reader used.

    read_region is 1-based into the file's own order, never into a score-sorted one.
    A letter prefix ("e1", "w1") asks for that region's wider view_e / view_w crop.
    """
    marker = roll.get("read_region")
    if not marker:
        return None, "view"
    variant, digits = re.fullmatch(r"([a-z]*)(\d+)", str(marker)).groups()
    regions = roll.get("regions") or []
    index = int(digits)
    if not 0 < index <= len(regions):
        return None, "view"
    return regions[index - 1], f"view_{variant}" if variant else "view"


def image(region, variant):
    """The wider, more readable box, as a IIIF box and rotation the page can resize."""
    return region.get(variant) or region.get("view")


def roll_entry(roll):
    region, variant = read_region(roll)
    picture = image(region, variant) if region else None
    entry = {
        "no": roll["welte_number"],
        "title": html.unescape(roll["title"] or ""),
        "performer": html.unescape(roll["performer"] or ""),
        "callnum": roll["callnum"],
        "inscription": roll.get("inscription"),
    }
    if roll.get("date_iso"):
        entry["date"] = roll["date_iso"]
    if picture:
        entry.update(picture)
    return entry


def year_counts(dated):
    counts = {}
    for roll in dated:
        year = int(roll["date_iso"][:4])
        counts[year] = counts.get(year, 0) + 1
    span = range(min(counts), max(counts) + 1)
    return [{"year": y, "count": counts.get(y, 0)} for y in span]


def registry(hands, by_druid):
    clusters = sorted(hands["clusters"], key=lambda c: -len(c["rolls"]))
    controllers = [
        {"n": n, "reading": c["reading"], "role": c["role"], "note": c["note"],
         "count": len(c["rolls"]),
         "rolls": sorted(c["rolls"], key=lambda d: by_druid[d].get("date") or "")}
        for n, c in enumerate(clusters, start=1)
    ]
    singles = sorted(hands["singles"], key=lambda s: by_druid[s["druid"]].get("date") or "")
    return controllers, singles


def main():
    rolls = json.loads(SOURCE.read_text())
    hands = json.loads(HANDS.read_text())

    scanned = [r for r in rolls if r.get("regions")]
    dated = [r for r in rolls if r.get("date_iso")]
    wanted = {d for c in hands["clusters"] for d in c["rolls"]}
    wanted |= {s["druid"] for s in hands["singles"]}
    wanted |= {r["druid"] for r in dated}

    by_druid = {r["druid"]: roll_entry(r) for r in rolls if r["druid"] in wanted}
    controllers, singles = registry(hands, by_druid)

    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(json.dumps({
        "generated": date.today().isoformat(),
        "totals": {"rolls": len(rolls), "scanned": len(scanned), "dated": len(dated)},
        "years": year_counts(dated),
        "rolls": by_druid,
        "controllers": controllers,
        "singles": singles,
    }, ensure_ascii=False, separators=(",", ":")))

    print(f"{len(rolls)} rolls, {len(scanned)} scanned, {len(dated)} dated")
    print(f"{len(controllers)} controllers, {len(singles)} single hands")
    print(f"wrote {TARGET.relative_to(HERE)} ({TARGET.stat().st_size // 1024} kB)")


if __name__ == "__main__":
    main()
