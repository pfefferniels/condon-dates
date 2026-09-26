# Dates and Hands of Condon Welte Rolls

A small static page showing when the red Welte rolls of the Condon collection at Stanford
were punched, and the hands that signed them.

The page is in `docs/` and is served by GitHub Pages. Images are hot-linked from Stanford's
IIIF endpoint; nothing is bundled.

## Data

`data/readings.json` is the record of what was read off each roll, keyed by druid: the
inscription, the date as written and as ISO, its confidence, the written roll number, the
hand, the reader's notes and the IIIF crop the reading was made from. Corrections are made
there and nowhere else. The readings were first made in `welte225.org/punch-225/dates`, and
`source` names the file there that each one came from.

`data/catalogue.json` holds what Stanford catalogues about each roll, whether it has a
scan and where the paper lies in it. `data/perforator.json` holds how the perforator was
set on each roll, from the two sweeps of punch-225: `pitch.json` (chain pitch, slot, bridge,
Teilung, the parser's hole width) and `step.json` (the advance). Both are refreshed from
punch-225 with `sync.py`, which also records the commit of welte225.org they came from; the
scripts that take the measurements stay there. `hands.json` holds the signature clusters.
`build.py` turns the four into `docs/data/rolls.json` and the linked data below.

## Linked data

Every roll is also published in the format of
[linked-rolls](https://github.com/pfefferniels/linked-rolls), as the `RollCopy` an edition
lists among its copies. It holds only what this repo knows about the copy: who keeps it
and where its scan is, which roll it is a copy of, the inscription on its paper and the
hand that wrote it, when it was punched, and how the perforator was set. A value that rests
on a judgement carries the belief it rests on, with its certainty and reasons, as
linked-rolls annotates any statement, so an edition can take the copy's date or setting
as a premise instead of restating it.

| File | Content |
|---|---|
| `docs/copies/<druid>.jsonld` | one copy, the document to cite |
| `docs/copies.jsonld` | the register, every copy in one document |
| `docs/hands.jsonld` | the hands of `hands.json`, which the copies name as actors |
| `docs/context.jsonld` | the terms linked-rolls does not have yet |

The IRIs are fragments of the document that states them, so they resolve on a static
host, and they are built from the druid and the role of the node, so a rebuild keeps
them. `copies/mf320jq4997.jsonld#copy` is Condon Roll 47; `#date-belief`, `#hand-belief`,
`#punch-diameter-belief`, `#chain-pitch-belief` and `#advance-belief` are the beliefs in
its punch date, its hand and its setting; `#inscription-text` is the transcription the
date and the hand are read from. Every record validates against the `RollCopy` of the
linked-rolls schema, and every term in it expands.

How a certainty is chosen is set at the top of `linked.py` and repeated in the reasons of
each belief. A date is true where every figure of its reading is plain, likely where one
is arguable, possible where the reading could be another date. A hand is likely where it
is clustered with other rolls by letterform, possible where it is only read. The chain
pitch is likely; the parser's hole width only possible, since it moves with the grey level
an edge is put at. An advance is held as `settings225.py` holds it for the edition of 225.

What it does not do yet:

- The IRIs stand on `pfefferniels.github.io` and change if the site moves. Nothing should
  cite them before a lasting base is chosen.
- No licence is stated.
- An inscription is placed by the crop it was read from, not by its ink, and on the scanner's
  track numbering rather than the tracker bar's, since no hole was read here to fix it.
- An act has one actor in linked-rolls, so a countersignature is named only in a note.
- Colour is not measured, and linked-rolls has no term for it.
