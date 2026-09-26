"""The premises for dating a Welte roll, as linked data.

The catalogue states no roll. It states what measuring all of them allows an edition to
conclude about any one: that a setting of the perforator, or a class of paper, was used
only before a day, only after one, or only between two. An edition
measures its own copy, states the measurement itself, and takes a premise from here to
date the copy, so that it stays whole on its own and each document reasons about what it
owns.

A premise is written as a production that stands for many copies, "the red rolls punched
with an advance of 1.0 mm", in the shape linked-rolls gives the production of a copy. Its
date carries the belief an edition names as a premise, and the reasons of that belief
link the dated copies it rests on, the data and the scripts, at the commits they stood at.

    docs/premises.jsonld         the premises, at premises
    docs/papers.jsonld           the classes of paper the premises name, at papers
    docs/evidence/<name>.json    the copies a premise rests on, at evidence/<name>, in groups,
                                 each naming the premise it bears on
    docs/premises.html           the page that shows them, for a reader who follows an IRI
    docs/context.jsonld          the terms linked-rolls does not have yet

Who signed the rolls is not a premise but an identity, and hands.py publishes it apart.

The IRIs stand on w3id.org, which w3id/welte-premises/.htaccess redirects to the files on
GitHub Pages. They are named after what they state, never numbered, so a rebuild keeps
them while the bounds and the certainty of a premise move with the evidence.
"""
import json
import statistics
import subprocess
from collections import Counter
from datetime import date
from pathlib import Path

import numpy as np

BASE = "https://w3id.org/welte-premises/"
LICENSE = "https://creativecommons.org/licenses/by/4.0/"
REO = "https://w3id.org/reo/context.jsonld"

PURL = "https://purl.stanford.edu"
CONDON_DATES = "https://github.com/pfefferniels/condon-dates/blob/{commit}/"
PUNCH_225 = "https://github.com/pfefferniels/welte225.org/blob/{commit}/punch-225/"

T100 = "https://w3id.org/reo/type/system/welte-t100"
WELTE = {"name": "M. Welte & Söhne", "sameAs": ["https://d-nb.info/gnd/5125268-5"]}
PUBLISHER = {"name": "Niels Pfeffer", "sameAs": []}

# A copy counts as dated where its date is held true or likely: a reading graded high or
# medium (punch-225/dates/reading.md), and dated to the day, since a bound is a day.
DATED = ("high", "medium")

# The advance counts where the slot lengths keep it at this strength, and it is the early
# setting in this band and the late one below the second figure; a period of 1.4 to 1.6 mm
# is noise (punch-225/dates/summary.py).
RESOLVED = 0.25
EARLY = (0.85, 1.15)
LATE = 0.75

# The classes of paper, by the colour paper/colour.py measures on a scan and corrects
# against the grey card hanging above its leader (CIELAB, D65). Four are kinds; two are
# narrower classes within a kind whose copies are dated closer together than chance
# allows, each with the band just outside its rule, to say what the rule's edge decides.
PAPERS = [
    {"id": "red-warm", "name": "warm red paper", "rule": "a* at least 10 and b* at least 15",
     "test": lambda l, a, b: a >= 10 and b >= 15},
    {"id": "red-warm-bright", "name": "bright warm red paper", "broader": "red-warm",
     "rule": "warm red with a* at least 32",
     "test": lambda l, a, b: a >= 32 and b >= 15, "edge": lambda l, a, b: 31 <= a < 32 and b >= 15},
    {"id": "red-cool", "name": "cool red paper", "rule": "a* at least 10 and b* under 15",
     "test": lambda l, a, b: a >= 10 and b < 15},
    {"id": "red-cool-light", "name": "light cool red paper", "broader": "red-cool",
     "rule": "cool red with L* at least 38",
     "test": lambda l, a, b: a >= 10 and b < 15 and l >= 38, "edge": lambda l, a, b: a >= 10 and b < 15 and 37 <= l < 38},
    {"id": "buff", "name": "buff paper", "rule": "a* from 3 to under 10", "test": lambda l, a, b: 3 <= a < 10},
    {"id": "green", "name": "green paper", "rule": "a* under 3", "test": lambda l, a, b: a < 3},
]

# What is stated of a class, and how firmly: a bound held likely rests on many dated
# copies, one held possible on a handful.
PAPER_PREMISES = [("red-cool", "after", "likely"), ("red-warm-bright", "between", "likely"),
                  ("red-cool-light", "between", "possible"), ("buff", "between", "possible"),
                  ("green", "between", "possible")]

WIDE = 2.75        # mm of chain pitch and over: the wide perforator (punch-225/README.md)
DRAWS = 10000      # random groups a narrower class's dates are held against


def head(repo):
    """The commit the checkout stands at, for linking a file as the premise used it."""
    found = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True)
    return found.stdout.strip() or "main"


def believed(name, certainty, reasons):
    return {"@annotation": {
        "@id": f"premises#{name}-annotation",
        "belief": {"@type": "belief", "@id": f"premises#{name}-belief",
                   "certainty": certainty, "reasons": reasons},
    }}


def copy_of(row):
    return f"Welte {row['welte']} of {row['date']} ({PURL}/{row['druid']})"


def advance_evidence(catalogue, readings, measured):
    """The dated copies whose advance resolves, early and late, in the order of their dates."""
    welte = {roll["druid"]: roll["welte_number"] for roll in catalogue}
    rows = {"early": [], "late": []}
    for druid, reading in readings.items():
        step = measured.get(druid, {}).get("step")
        date = reading.get("date_iso") or ""
        if not step or step["strength"] < RESOLVED or reading["confidence"] not in DATED or len(date) != 10:
            continue
        band = ("early" if EARLY[0] <= step["advance"] <= EARLY[1]
                else "late" if step["advance"] < LATE else None)
        if band:
            rows[band].append({"druid": druid, "welte": welte[druid], "date": date,
                               "advance": step["advance"], "strength": step["strength"]})
    return {band: sorted(found, key=lambda row: row["date"]) for band, found in rows.items()}


def setting(name, advance):
    return {"@type": "Perforator", "@id": f"premises#{name}-perforator",
            "condition": {"conditionType": "setting", "advance": {"value": advance, "unit": "mm"}}}


def advance_premises(evidence, used):
    early, late = evidence["early"], evidence["late"]
    last_early, first_late = early[-1], late[0]
    counted = (f"The advance resolves, at a strength of at least {RESOLVED}, at {EARLY[0]} to {EARLY[1]} mm "
               f"on {len(early)} copies dated to the day at high or medium confidence, from "
               f"{early[0]['date']} to {last_early['date']}, and under {LATE} mm on {len(late)}, from "
               f"{first_late['date']} to {late[-1]['date']}; no dated copy falls on the wrong side.")
    return [
        {"@id": "premises#advance-1mm", "company": WELTE, "system": {"@id": T100},
         "perforator": setting("advance-1mm", statistics.median(row["advance"] for row in early)),
         "date": {"before": first_late["date"], **believed("advance-1mm", "likely", [{
             "@type": "inference", "premises": [], "used": used,
             "note": f"{counted} The perforator was re-set to the late advance by the day of the first late "
                     f"copy, {copy_of(first_late)}, and the bound rests on that copy's date alone. The early "
                     "advance resolves on the rolls of three hands only, and on none before 1908, so it is "
                     "attested on fewer rolls than it was used on (punch-225/dates/README.md)."}])}},
        {"@id": "premises#advance-half-mm", "company": WELTE, "system": {"@id": T100},
         "perforator": setting("advance-half-mm", statistics.median(row["advance"] for row in late)),
         "date": {"after": last_early["date"], **believed("advance-half-mm", "likely", [{
             "@type": "inference", "premises": [], "used": used,
             "note": f"{counted} The perforator was still at the early advance on the day of the last early "
                     f"copy, {copy_of(last_early)}, and the bound rests on that copy's date alone. The rolls "
                     "before it that do not resolve are not late-advance rolls hiding: a comb at 0.5 mm is the "
                     "easier of the two to see (punch-225/dates/README.md)."}])}},
    ]


def year(iso):
    day = date.fromisoformat(iso)
    return day.year + (day.timetuple().tm_yday - 1) / 365.25


def spread(dates):
    """The years between the tenth and the ninetieth percentile of the dates."""
    years = np.array([year(d) for d in dates])
    return float(np.subtract(*np.percentile(years, [90, 10])))


def paper_evidence(catalogue, readings, colours, measured):
    """Each class of paper with the copies measured as of it and those of them dated to the day."""
    welte = {roll["druid"]: roll["welte_number"] for roll in catalogue}
    lab = {druid: e["corrected"]["lab"] for druid, e in colours.items() if e.get("corrected")}
    rgb = {druid: [round(v) for v in e["corrected"]["rgb"]] for druid, e in colours.items() if e.get("corrected")}
    dated = {druid: r["date_iso"] for druid, r in readings.items()
             if druid in lab and r["confidence"] in DATED and len(r.get("date_iso") or "") == 10}
    pitch = {druid: m.get("pitch", {}).get("pitch") for druid, m in measured.items()}
    classes = {}
    for paper in PAPERS:
        members = [druid for druid in lab if paper["test"](*lab[druid])]
        copies = sorted(({"druid": d, "welte": welte[d], "date": dated[d], "lab": lab[d], "rgb": rgb[d]}
                         for d in members if d in dated), key=lambda row: row["date"])
        machines = Counter("wide" if pitch[d] >= WIDE else "narrow" for d in members if pitch.get(d))
        edge = [dated[d] for d in lab if d in dated and paper.get("edge", lambda *_: False)(*lab[d])]
        classes[paper["id"]] = {**paper, "members": len(members), "copies": copies, "machines": machines,
                                "edge": sorted(edge)}
    return classes, dated


def chance(narrow, broad):
    """How often random groups of the broader class's dated copies are as close in date as the narrower."""
    rng = np.random.default_rng(0)
    pool = [row["date"] for row in broad["copies"]]
    observed = spread([row["date"] for row in narrow["copies"]])
    draws = np.array([spread(rng.choice(pool, len(narrow["copies"]), replace=False)) for _ in range(DRAWS)])
    return observed, float(np.median(draws)), int((draws <= observed).sum())


def paper_note(paper, bound, classes, dated):
    copies, first, last = paper["copies"], paper["copies"][0], paper["copies"][-1]
    note = [f"{paper['members']} rolls measure as {paper['name']} ({paper['rule']}, corrected CIELAB), "
            f"{len(copies)} of them dated to the day at high or medium confidence, from {first['date']} "
            f"to {last['date']}."]
    wide, narrow = paper["machines"]["wide"], paper["machines"]["narrow"]
    note.append(f"All {narrow} whose chain pitch is measured were punched on the narrow perforator." if not wide
                else f"{wide} of them {'was' if wide == 1 else 'were'} punched on the wide perforator and "
                     f"{narrow} on the narrow one.")
    if bound == "after":
        before = sum(1 for d in dated.values() if d < first["date"])
        note.append(f"The bound rests on the first dated copy, {copy_of(first)}, alone; the {before} "
                    "dated copies before it are all of other paper.")
    else:
        note.append(f"The bounds rest on the first and the last dated copy, {copy_of(first)} and {copy_of(last)}.")
    if paper.get("broader"):
        broad = classes[paper["broader"]]
        observed, median, as_close = chance(paper, broad)
        note.append(f"Its dates lie closer together than chance allows: {observed:.1f} years between the tenth and "
                    f"the ninetieth percentile, against {median:.1f} years for random groups of as many dated "
                    f"copies of {broad['name']}, of which {as_close} in {DRAWS} were as close.")
        outside = [d for d in paper["edge"] if not first["date"] <= d <= last["date"]]
        note.append(f"Within a unit of the rule's edge lie {len(paper['edge'])} dated copies"
                    + ((f"; that of {outside[0]} lies" if len(outside) == 1 else f"; those of {', '.join(outside)} lie")
                       + " outside the window and would widen it under a looser rule." if outside
                       else ", all inside the window."))
    if len(copies) < 10:
        note.append(f"The class is attested on {len(copies)} dated copies only.")
    return " ".join(note)


def paper_premises(classes, dated, used):
    productions = []
    for pid, bound, certainty in PAPER_PREMISES:
        paper = classes[pid]
        first, last = paper["copies"][0]["date"], paper["copies"][-1]["date"]
        span = {"after": first} if bound == "after" else {"after": first, "before": last}
        name = f"paper-{pid}"
        productions.append({
            "@id": f"premises#{name}", "company": WELTE, "system": {"@id": T100},
            "paper": {"@id": f"papers#{pid}", "name": paper["name"]},
            "date": {**span, **believed(name, certainty, [{
                "@type": "inference", "premises": [], "used": used,
                "note": paper_note(paper, bound, classes, dated)}])},
        })
    return productions


def papers_document(classes, method):
    return {
        "@context": contexts(),
        "@id": "papers",
        "title": "Classes of paper of the red Welte rolls, by their colour",
        "license": LICENSE,
        "comment": "Each class is defined by the colour of the blank paper as paper/colour.py measures it on a "
                   "scan, corrected against the grey card scanned above the leader, in CIELAB with a D65 white. "
                   "The rules were drawn on Stanford's scans of the Condon collection, all from one scanner.",
        "@included": [{"@id": f"papers#{p['id']}", "name": p["name"], "seeAlso": method,
                       "comment": f"Paper whose corrected colour has {p['rule']}.",
                       **({"broader": f"papers#{p['broader']}"} if p.get("broader") else {})}
                      for p in classes.values()],
    }


def context():
    """The terms a catalogue of premises needs and linked-rolls does not yet have.

    `productions` takes the scoped context REO gives a copy's `production`, so that a
    premise reads its perforator and its system as a copy's production does.
    """
    return {"@context": {
        "comment": "rdfs:comment",
        "seeAlso": {"@id": "rdfs:seeAlso", "@type": "@id"},
        "broader": {"@id": "http://www.w3.org/2004/02/skos/core#broader", "@type": "@id"},
        "productions": {"@id": "crm:P70_documents", "@context": {
            "system": "crm:P32_used_general_technique",
            "perforator": {"@id": "crm:P16_used_specific_object", "@context": {
                "punchDiameter": "reo:punchDiameter", "chainPitch": "reo:chainPitch", "advance": "reo:advance",
                "slot": "reo:slot", "bridge": "reo:bridge", "n": "reo:sampleSize", "strength": "reo:strength",
                "value": "crm:P90_has_value"}},
        }},
    }}


def contexts():
    return [REO, BASE + "context.jsonld", {"@base": BASE}]


def write(target, document, indent=1):
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(document, ensure_ascii=False, indent=indent) + "\n")


def build(docs, catalogue, readings, perforator, colours, published):
    """Write the premises, the paper classes, their evidence and the context into docs/."""
    here = Path(__file__).parent
    condon = CONDON_DATES.format(commit=head(here))
    evidence = advance_evidence(catalogue, readings, perforator["rolls"])
    write(docs / "evidence" / "advance.json", {
        "rule": f"dated to the day at confidence {' or '.join(DATED)}; advance at strength {RESOLVED} or more",
        "quantity": "advance",
        "unit": "mm",
        "groups": [
            {"id": "early", "label": f"advance {EARLY[0]} to {EARLY[1]} mm", "premise": "advance-1mm",
             "copies": evidence["early"]},
            {"id": "late", "label": f"advance under {LATE} mm", "premise": "advance-half-mm",
             "copies": evidence["late"]},
        ],
    })
    used = [BASE + "evidence/advance", condon + "data/readings.json", condon + "data/perforator.json",
            condon + "premises.py", PUNCH_225.format(commit=perforator["commit"] or "main") + "dates/step.py"]
    productions = advance_premises(evidence, used)

    classes, dated = paper_evidence(catalogue, readings, colours, perforator["rolls"])
    premised = dict((pid, f"paper-{pid}") for pid, _, _ in PAPER_PREMISES)
    write(docs / "evidence" / "paper.json", {
        "rule": f"dated to the day at confidence {' or '.join(DATED)}; colour as paper/colour.py measures it, "
                "corrected against the grey card",
        "quantity": "lab",
        "unit": "L* a* b*",
        "groups": [{"id": pid, "label": f"{c['name']}, {c['rule']}", "premise": premised.get(pid),
                    "copies": c["copies"]} for pid, c in classes.items()],
    })
    write(docs / "papers.jsonld", papers_document(classes, condon + "paper/colour.py"))
    productions += paper_premises(classes, dated, [
        BASE + "evidence/paper", BASE + "papers", condon + "paper/colour.json", condon + "paper/colour.py",
        condon + "data/readings.json", condon + "data/perforator.json", condon + "premises.py"])
    write(docs / "premises.jsonld", {
        "@context": contexts(),
        "@id": "premises",
        "title": "Premises for dating Welte rolls",
        "license": LICENSE,
        "creation": {"publisher": PUBLISHER, "publicationDate": published},
        "productions": productions,
    })
    write(docs / "context.jsonld", context())
    return productions
