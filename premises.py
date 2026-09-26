"""The premises for dating a Welte roll, as linked data.

The catalogue states no roll. It states what measuring all of them allows an edition to
conclude about any one: that a setting of the perforator was used only before or only
after a day, and, once the paper is classified, that a kind of paper was. An edition
measures its own copy, states the measurement itself, and takes a premise from here to
date the copy, so that it stays whole on its own and each document reasons about what it
owns.

A premise is written as a production that stands for many copies, "the red rolls punched
with an advance of 1.0 mm", in the shape linked-rolls gives the production of a copy. Its
date carries the belief an edition names as a premise, and the reasons of that belief
link the dated copies it rests on, the data and the scripts, at the commits they stood at.

    docs/premises.jsonld         the premises, at premises
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
from pathlib import Path

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


def context():
    """The terms a catalogue of premises needs and linked-rolls does not yet have.

    `productions` takes the scoped context REO gives a copy's `production`, so that a
    premise reads its perforator and its system as a copy's production does.
    """
    return {"@context": {
        "comment": "rdfs:comment",
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


def build(docs, catalogue, readings, perforator, published):
    """Write the premises, their evidence and the context into docs/."""
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
