#!/usr/bin/env python3
"""Regenerate docs/data/rolls.json and the premises from the catalogue, the readings, the
signature clustering and the perforator measurements.

All four live in this repo, so a clone rebuilds the site on its own. data/readings.json
is the record of what was read off each roll and is corrected by hand here. Refresh
data/catalogue.json and data/perforator.json with sync.py when punch-225 re-indexes or
re-measures the rolls. premises.py writes the premises the measurements allow, hands.py
the hands as authority records.
"""
import html
import json
import re
from collections import Counter
from datetime import date
from pathlib import Path

import hands as hand_records
import premises

HERE = Path(__file__).parent
CATALOGUE = HERE / "data" / "catalogue.json"
READINGS = HERE / "data" / "readings.json"
HANDS = HERE / "hands.json"
PERFORATOR = HERE / "data" / "perforator.json"
DOCS = HERE / "docs"
TARGET = DOCS / "data" / "rolls.json"

ISO_DATE = re.compile(r"\d{4}(-\d{2}(-\d{2})?)?")


def check(readings, measured, druids):
    """Refuse a hand edit the page would otherwise drop or mis-sort without a word."""
    unknown = sorted(readings.keys() - druids)
    malformed = sorted(d for d, r in readings.items()
                       if r.get("date_iso") and not ISO_DATE.fullmatch(r["date_iso"]))
    if unknown or malformed:
        raise SystemExit(f"readings.json: unknown druids {unknown}, malformed date_iso {malformed}")
    if measured.keys() - druids:
        raise SystemExit(f"perforator.json: unknown druids {sorted(measured.keys() - druids)}")


def roll_entry(roll, reading):
    entry = {
        "no": roll["welte_number"],
        "title": html.unescape(roll["title"] or ""),
        "performer": html.unescape(roll["performer"] or ""),
        "callnum": roll["callnum"],
        "inscription": reading.get("inscription"),
    }
    if reading.get("date_iso"):
        entry["date"] = reading["date_iso"]
    if reading.get("crop"):
        entry.update(reading["crop"])
    return entry


def year_counts(dates):
    counts = Counter(int(d[:4]) for d in dates)
    return [{"year": y, "count": counts[y]} for y in range(min(counts), max(counts) + 1)]


def registry(hands, by_druid):
    clusters = sorted(hands["clusters"], key=lambda c: -len(c["rolls"]))
    controllers = [
        {"n": n, "id": c["id"], "reading": c["reading"], "role": c["role"], "note": c["note"],
         "count": len(c["rolls"]),
         "rolls": sorted(c["rolls"], key=lambda d: by_druid[d].get("date") or "")}
        for n, c in enumerate(clusters, start=1)
    ]
    singles = sorted(hands["singles"], key=lambda s: by_druid[s["druid"]].get("date") or "")
    return controllers, singles


def main():
    rolls = json.loads(CATALOGUE.read_text())
    readings = json.loads(READINGS.read_text())
    hands = json.loads(HANDS.read_text())
    perforator = json.loads(PERFORATOR.read_text())
    check(readings, perforator["rolls"], {r["druid"] for r in rolls})

    dated = {d for d, r in readings.items() if r.get("date_iso")}
    wanted = {d for c in hands["clusters"] for d in c["rolls"]}
    wanted |= {s["druid"] for s in hands["singles"]}
    wanted |= dated

    by_druid = {r["druid"]: roll_entry(r, readings.get(r["druid"], {}))
                for r in rolls if r["druid"] in wanted}
    controllers, singles = registry(hands, by_druid)
    scanned = sum(1 for r in rolls if r["scanned"])

    today = date.today().isoformat()
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(json.dumps({
        "generated": today,
        "totals": {"rolls": len(rolls), "scanned": scanned, "dated": len(dated)},
        "years": year_counts(readings[d]["date_iso"] for d in dated),
        "rolls": by_druid,
        "controllers": controllers,
        "singles": singles,
    }, ensure_ascii=False, separators=(",", ":")))

    print(f"{len(rolls)} rolls, {scanned} scanned, {len(dated)} dated")
    print(f"{len(controllers)} controllers, {len(singles)} single hands")
    print(f"wrote {TARGET.relative_to(HERE)} ({TARGET.stat().st_size // 1024} kB)")

    stated = premises.build(DOCS, rolls, readings, perforator, today)
    named = hand_records.build(DOCS, hands)
    print(f"wrote {len(stated)} premises to docs/premises.jsonld with their evidence in docs/evidence/, "
          f"and {len(named)} hands to docs/hands.jsonld")


if __name__ == "__main__":
    main()
