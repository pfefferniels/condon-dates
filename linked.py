"""The rolls as linked data, in the format of linked-rolls.

Each roll is written as a linked-rolls RollCopy, the node an edition lists among its
copies, holding only what this repo knows about the copy: who keeps it and where its scan
is, which roll it is a copy of, the inscription on its paper and the hand that wrote it,
when it was punched, and how the perforator was set. Every value that rests on a judgement
carries the belief it rests on, as linked-rolls annotates a statement, and every belief
has an IRI of its own, so that an edition can take it as the premise of its own.

    docs/copies/<druid>.jsonld   one copy, the document to cite
    docs/copies.jsonld           the register, every copy in one document
    docs/hands.jsonld            the hands of hands.json, which the copies name as actors
    docs/context.jsonld          the terms linked-rolls does not have yet

The IRIs are fragments of the document that states them, so they resolve on a static
host: copies/mf320jq4997.jsonld#copy is the roll, #date-belief the belief in its date.
They are built from the druid and the role of the node and never from a random number,
so that a rebuild keeps them.
"""
import calendar
import html
import json
from pathlib import Path

BASE = "https://pfefferniels.github.io/condon-dates/"
REO = "https://w3id.org/reo/context.jsonld"

STACKS = "https://stacks.stanford.edu/image/iiif"
PURL = "https://purl.stanford.edu"
ANALYSES = "https://raw.githubusercontent.com/pianoroll/piano-roll-analyses/main/analysis"
PUNCH_225 = "https://github.com/pfefferniels/welte225.org/blob/{commit}/punch-225/"

T100 = "https://w3id.org/reo/type/system/welte-t100"
WELTE = {"name": "M. Welte & Söhne", "sameAs": []}
KEEPER = {"name": "Stanford University Libraries", "sameAs": []}
PUBLISHER = {"name": "Niels Pfeffer", "sameAs": []}

DPI = 300.25                  # SUPRA's resolution, along the roll and across it
MM_PER_INCH = 25.4
TEILUNG = 3.194               # mm, the median track pitch of the red rolls, where a scan gives none

# How sure a date is, from how plain its reading is (punch-225/dates/reading.md): every
# figure plain, one figure arguable with the date not in doubt, or a reading that could
# be another date.
DATED = {"high": "true", "medium": "likely", "low": "possible"}

# A hand clustered by letterform with other rolls is likely the one named; one read off
# a single roll, possibly.
CLUSTERED, UNCLUSTERED = "likely", "possible"

# The chain pitch survives the grey level an edge is put at; the parser's hole width
# does not, and moves by about 0.11 mm with it (punch-225/README.md).
PITCH_CERTAINTY, DIAMETER_CERTAINTY = "likely", "possible"

# An advance is held likely when found at this strength with the pitch within this much
# of a whole number of it, possible when one of the two holds (punch-225/dates/settings225.py).
LEAST_STRENGTH, WHOLE = 0.35, 0.15


def iri(druid, part=None):
    return f"copies/{druid}.jsonld" + (f"#{part}" if part else "")


def believed(druid, name, certainty, reasons):
    """The annotation of a statement, with the belief in it named after what it is about."""
    return {"@annotation": {
        "@id": iri(druid, f"{name}-annotation"),
        "belief": {"@type": "belief", "@id": iri(druid, f"{name}-belief"),
                   "certainty": certainty, "reasons": reasons},
    }}


def mm(pixels):
    return round(pixels / DPI * MM_PER_INCH, 2)


def scan_of(druid):
    return f"{STACKS}/{druid}%2F{druid}_0001/"


def analysis_of(druid):
    return f"{ANALYSES}/{druid[0]}/{druid}_analysis.txt.bz2"


def span(iso):
    """The day a punch date falls within, or the bounds of the month or year it gives."""
    if len(iso) == 10:
        return {"within": iso}
    year, month = int(iso[:4]), int(iso[5:7]) if len(iso) == 7 else None
    first, last = (month, month) if month else (1, 12)
    return {"after": f"{year:04d}-{first:02d}-01",
            "before": f"{year:04d}-{last:02d}-{calendar.monthrange(year, last)[1]:02d}"}


def medium_of(notes):
    first = (notes or "").split(",")[0].split(".")[0].strip().lower()
    return first if first in ("pencil", "ink", "crayon") else None


def inscription(druid, roll, reading, teilung):
    """The writing the date and the hand were read from, placed on the paper by its crop.

    The span along the roll is the crop's, from the first row of the scan as linked-rolls
    reads a Stanford analysis. The tracks are the scanner's numbering by linked-rolls'
    fallback calibration, the bass edge of the paper and one and a half tracks: no hole
    was read here to fix the tracker bar's, which lies within a few tracks of it. The
    crop is the region the reading was made from, not the extent of the ink.
    """
    x, y, w, h = map(int, reading["crop"]["box"].split(","))
    separation = (teilung or TEILUNG) / MM_PER_INCH * DPI
    offset = roll["paper"][0] + 1.5 * separation
    writing = {
        "@type": "Writing",
        "@id": iri(druid, "inscription"),
        "technique": "handwriting",
        "horizontal": {"unit": "mm", "from": mm(y), "to": mm(y + h)},
        "vertical": {"unit": "track", "from": int((x - offset) // separation),
                     "to": -int(-(x + w - offset) // separation)},
        "depiction": f"{scan_of(druid)}{reading['crop']['box']}/full/{reading['crop']['rot']}/default.jpg",
        "transcription": {"@type": "text", "@id": iri(druid, "inscription-text"),
                          "text": reading["inscription"]},
    }
    medium = medium_of(reading["notes"])
    return {**writing, "medium": medium} if medium else writing


def comprehension(druid, note):
    reason = {"@type": "meaningComprehension", "comprehends": [iri(druid, "inscription-text")]}
    return {**reason, "note": note} if note else reason


def hand(druid, reading, clusters, single):
    """Who wrote the inscription: a clustered hand by its IRI, else the name read off it."""
    signer = next((c for c in clusters if c["role"] == "signature"), clusters[0] if clusters else None)
    name = signer["reading"] if signer else (single or {}).get("reading") or reading["hand"]
    if not name:
        return None
    read = f'Read as "{reading["hand"]}".' if reading["hand"] else "No name was read off it."
    source = reading.get("hand_source")
    notes = [read, source and f"{source[0].upper()}{source[1:].rstrip('.')}."]
    notes += [f'Countersigned by {c["reading"]} ({BASE}hands.jsonld#{c["id"]}); an act has one actor '
              "in linked-rolls, so the countersignature is stated here only." for c in clusters if c is not signer]
    reasons = [comprehension(druid, " ".join(n for n in notes if n))]
    if signer:
        reasons.append({"@type": "inference", "premises": [], "used": [f"{BASE}hands.jsonld"],
                        "note": "The signature is clustered with the hand's other rolls by comparing "
                                "the inscription images, not by the name read."})
    actor = {"name": name, "sameAs": [], **({"@id": f"hands.jsonld#{signer['id']}"} if signer else {})}
    return {**actor, **believed(druid, "hand", CLUSTERED if signer else UNCLUSTERED, reasons)}


def dating(druid, reading):
    certainty = DATED.get(reading["confidence"])
    if not reading["date_iso"] or not certainty:
        return None
    return {**span(reading["date_iso"]),
            **believed(druid, "date", certainty, [comprehension(druid, reading["notes"])])}


def measured(note, *used):
    return [{"@type": "measurement", "note": note, "used": list(used)}]


def setting(druid, measure, commit):
    """How the perforator was set, from the two sweeps of punch-225."""
    script = PUNCH_225.format(commit=commit or "main")
    pitch, step = measure.get("pitch", {}), measure.get("step", {})
    found = {}
    if pitch.get("avg_hole_width"):
        found["punchDiameter"] = {"value": pitch["avg_hole_width"], "unit": "mm", **believed(
            druid, "punch-diameter", DIAMETER_CERTAINTY, measured(
                "AVG_HOLE_WIDTH of the roll's SUPRA analysis: the parser's box at its own grey level, "
                "averaged over every perforation it kept, so that a tear or a run of dust drags it. "
                "On the three copies measured both ways, an edge at half the contrast put the punch "
                "0.10 to 0.15 mm wider (punch-225/README.md).",
                analysis_of(druid), script + "dates/pitch.py"))}
    if pitch.get("pitch"):
        found["chainPitch"] = {"value": pitch["pitch"], "unit": "mm", "slot": pitch["slot"],
                               "bridge": pitch["bridge"], "n": pitch["n"], **believed(
            druid, "chain-pitch", PITCH_CERTAINTY, measured(
                f"Median over {pitch['n']} pitches of held notes, measured on the IIIF image by "
                "punch-225/dates/pitch.py; slot and bridge are medians of their own.",
                scan_of(druid), script + "dates/pitch.py"))}
    if step.get("advance"):
        strong = step["strength"] >= LEAST_STRENGTH
        steps = pitch["pitch"] / step["advance"] if pitch.get("pitch") else None
        whole = steps is not None and abs(steps - round(steps)) <= WHOLE
        others = ", ".join(f"{p} mm at {r}" for p, r in step["others"] if p != step["advance"])
        ratio = f" The chain pitch is {steps:.3f} of it." if steps else ""
        found["advance"] = {"value": step["advance"], "unit": "mm", "strength": step["strength"],
                            "n": step["n"], **believed(
            druid, "advance", "likely" if strong and whole else "possible" if strong or whole else "unlikely",
            measured(f"The strongest period the {step['n']} slot lengths keep, by punch-225/advance.py "
                     f"(punch-225/dates/step.py); runners-up {others}.{ratio} Held likely when found at a "
                     f"strength of at least {LEAST_STRENGTH} with the pitch within {WHOLE} of a whole number "
                     "of it, possible when one of the two holds, unlikely when neither does.",
                     analysis_of(druid), script + "dates/step.py"))}
    if not found:
        return None
    return {"@type": "Perforator", "@id": iri(druid, "perforator"),
            "condition": {"conditionType": "setting", **found}}


def copy_of(roll, reading, clusters, single, measure, commit):
    druid = roll["druid"]
    teilung = measure.get("pitch", {}).get("teilung")
    copy = {
        "@type": "RollCopy",
        "@id": iri(druid, "copy"),
        "label": f"Condon Roll {roll['callnum'].rsplit(' ', 1)[-1]}",
        "identifier": roll["callnum"],
        "seeAlso": f"{PURL}/{druid}",
        "exemplifies": {
            "catalogueNumber": f"WM {roll['welte_number']}",
            "label": ": ".join(html.unescape(s) for s in (roll["performer"], roll["title"]) if s),
        },
        "keeper": KEEPER,
        "conditions": [],
        "measurements": {},
        "modifications": [],
    }
    if roll["scanned"]:
        copy["scan"] = scan_of(druid)
        copy["readFrom"] = {"kind": "scan"}
        copy["measurements"]["scanResolution"] = {"value": DPI, "unit": "px/in"}
    if teilung:
        copy["measurements"]["holeSeparation"] = {"value": teilung, "unit": "mm"}

    production = {"company": WELTE, "system": {"@id": T100}}
    written = reading.get("inscription") and reading.get("crop") and (reading["date_iso"] or reading["hand"] or clusters)
    if written:
        act = {"@type": "Alteration", "purpose": "control",
               "produced": [inscription(druid, roll, reading, teilung)]}
        actor = hand(druid, reading, clusters, single)
        copy["modifications"].append({**act, "actor": actor} if actor else act)
        date = dating(druid, reading)
        if date:
            production["date"] = date
    perforator = setting(druid, measure, commit)
    if perforator:
        production["perforator"] = perforator
    copy["production"] = production
    return copy


def context():
    return {"@context": {
        "label": "rdfs:label",
        "comment": "rdfs:comment",
        "identifier": "dcterms:identifier",
        "seeAlso": {"@id": "rdfs:seeAlso", "@type": "@id"},
        "isPartOf": {"@id": "dcterms:isPartOf", "@type": "@id"},
        "exemplifies": "lrmoo:R7_exemplifies",
    }}


def contexts():
    return [REO, BASE + "context.jsonld", {"@base": BASE}]


def hands_document(hands):
    return {
        "@context": contexts(),
        "@id": "hands.jsonld",
        "title": "The hands that signed the Condon Welte rolls",
        "comment": hands["_"],
        "@included": [{"@id": f"hands.jsonld#{c['id']}", "name": c["reading"], "sameAs": [],
                       "comment": c["note"]} for c in hands["clusters"]],
    }


def write(target, document, indent=None):
    target.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(document, ensure_ascii=False, indent=indent,
                      separators=None if indent else (",", ":"))
    target.write_text(text + "\n")


def build(docs, catalogue, readings, hands, perforator, published):
    """Write the register, one document per copy, the hands and the context into docs/."""
    clusters = {}
    for cluster in hands["clusters"]:
        for druid in cluster["rolls"]:
            clusters.setdefault(druid, []).append(cluster)
    singles = {s["druid"]: s for s in hands["singles"]}
    measures = perforator["rolls"]

    copies = [copy_of(roll, readings.get(roll["druid"], {}), clusters.get(roll["druid"], []),
                      singles.get(roll["druid"]), measures.get(roll["druid"], {}), perforator["commit"])
              for roll in catalogue]

    for copy in copies:
        document = copy["@id"].split("#")[0]
        write(docs / document, {"@context": contexts(), "@id": document,
                                "title": f"{copy['label']}, {copy['exemplifies']['catalogueNumber']}",
                                "isPartOf": "copies.jsonld", "copies": [copy]}, indent=1)
    write(docs / "copies.jsonld", {
        "@context": contexts(),
        "@id": "copies.jsonld",
        "title": "The red Welte rolls of the Condon collection at Stanford",
        "creation": {"publisher": PUBLISHER, "publicationDate": published},
        "copies": copies,
    })
    write(docs / "hands.jsonld", hands_document(hands), indent=1)
    write(docs / "context.jsonld", context(), indent=1)
    return copies
