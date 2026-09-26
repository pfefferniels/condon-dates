#!/usr/bin/env python3
"""Regenerate the site and the premises from what this repository holds.

Everything lives here, so a clone rebuilds the site on its own. data/readings.json is the
record of what was read off each roll and is corrected by hand here. The index of the rolls
comes from the search of the scans in dates/candidates.json, the perforator from the two
sweeps in perforator/, the paper from paper/, the hands from hands.json. data/catalogue.json
and data/perforator.json are written from them on every build, as the trimmed views the
other scripts read; they are not edited. premises.py writes the premises the measurements
allow, hands.py the hands as authority records.
"""
import html
import json
import re
from collections import Counter
from datetime import date
from pathlib import Path

import numpy as np

import hands as hand_records
import premises

HERE = Path(__file__).parent
CANDIDATES = HERE / "dates" / "candidates.json"
SWEEPS = HERE / "perforator"
CATALOGUE = HERE / "data" / "catalogue.json"
READINGS = HERE / "data" / "readings.json"
HANDS = HERE / "hands.json"
PERFORATOR = HERE / "data" / "perforator.json"
COLOURS = HERE / "paper" / "colour.json"
RULINGS = HERE / "paper" / "ruling.json"
DOCS = HERE / "docs"
TARGET = DOCS / "data" / "rolls.json"
MEASURES = DOCS / "data" / "measures.json"

ISO_DATE = re.compile(r"\d{4}(-\d{2}(-\d{2})?)?")

ROLL_FIELDS = ("druid", "welte_number", "callnum", "title", "performer")


def index():
    """Write the trimmed views of the scan search and the two sweeps that the scripts read.

    The catalogue keeps what Stanford catalogues about each roll, whether it has a scan and
    where the paper lies in it; the perforator keeps each roll's row of pitch.json and of
    step.json, a row that measured nothing being left out.
    """
    rolls = json.loads(CANDIDATES.read_text())
    CATALOGUE.write_text(json.dumps([
        {**{f: roll.get(f) for f in ROLL_FIELDS}, "scanned": bool(roll.get("regions")),
         "paper": roll.get("paper_columns"), "length": roll.get("image_length"),
         "holes": [roll.get("first_hole"), roll.get("last_hole")]} for roll in rolls
    ], ensure_ascii=False, separators=(",", ":")))
    sweeps = {name: {row["druid"]: {k: v for k, v in row.items() if k != "druid"}
                     for row in json.loads((SWEEPS / f"{name}.json").read_text()) if row.get("n")}
              for name in ("pitch", "step")}
    PERFORATOR.write_text(json.dumps({"rolls": {
        druid: {name: sweeps[name][druid] for name in ("pitch", "step") if druid in sweeps[name]}
        for druid in sorted(sweeps["pitch"].keys() | sweeps["step"].keys())
    }}, ensure_ascii=False, separators=(",", ":")))


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


def measures(rolls, readings, perforator, colours, rulings):
    """Every scanned roll's paper and perforator, with its date where it is held true or likely.

    The page shows the corpus from it: the colour of every roll, the class of paper that
    colour falls in, and the pitch and advance of the perforator against the date.
    """
    kinds = [p for p in premises.PAPERS if not p.get("broader")]
    narrower = [p for p in premises.PAPERS if p.get("broader")]
    entries = {}
    for roll in rolls:
        druid, reading = roll["druid"], readings.get(roll["druid"], {})
        colour = colours.get(druid, {}).get("corrected")
        measured = perforator["rolls"].get(druid, {})
        entry = {"no": roll["welte_number"]}
        if reading.get("date_iso") and reading["confidence"] in premises.DATED:
            entry["date"] = reading["date_iso"]
        if colour:
            entry.update(lab=colour["lab"], rgb=[round(v) for v in colour["rgb"]],
                         paper=next(p["id"] for p in kinds if p["test"](*colour["lab"])))
            batch = next((p["id"] for p in narrower if p["test"](*colour["lab"])), None)
            if batch:
                entry["batch"] = batch
        if rulings.get(druid, {}).get("call") == "ruled":
            entry["ruled"] = True
        if measured.get("pitch", {}).get("pitch"):
            entry["pitch"] = measured["pitch"]["pitch"]
        step = measured.get("step")
        if step and step["strength"] >= premises.RESOLVED:
            entry["advance"] = step["advance"]
        if len(entry) > 1:
            entries[druid] = entry

    papers = []
    for paper in [*premises.PAPERS, premises.RULED]:
        members = [e for e in entries.values()
                   if paper["id"] in (e.get("paper"), e.get("batch")) or (paper["id"] == "ruled" and e.get("ruled"))]
        days = sorted(e["date"] for e in members if len(e.get("date", "")) == 10)
        papers.append({"id": paper["id"], "name": paper["name"], "rule": paper["rule"],
                       "broader": paper.get("broader"), "ruled": paper["id"] == "ruled",
                       "count": len(members), "dated": len(days),
                       "span": [days[0], days[-1]] if days else None,
                       "rgb": [round(float(v)) for v in np.median([e["rgb"] for e in members], 0)]})
    MEASURES.write_text(json.dumps({"papers": papers, "rolls": entries}, ensure_ascii=False, separators=(",", ":")))
    return entries


def main():
    index()
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

    colours = json.loads(COLOURS.read_text())
    rulings = json.loads(RULINGS.read_text())
    stated = premises.build(DOCS, rolls, readings, perforator, colours, rulings, today)
    measured = measures(rolls, readings, perforator, colours, rulings)
    print(f"wrote the paper and perforator of {len(measured)} rolls to {MEASURES.relative_to(HERE)} "
          f"({MEASURES.stat().st_size // 1024} kB)")
    named = hand_records.build(DOCS, hands)
    print(f"wrote {len(stated)} premises to docs/premises.jsonld with their evidence in docs/evidence/, "
          f"and {len(named)} hands to docs/hands.jsonld")


if __name__ == "__main__":
    main()
