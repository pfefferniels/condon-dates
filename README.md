# Condon Welte rolls

The red Welte rolls of the Condon collection at Stanford Libraries: when they were punched,
who signed them, the paper they were cut on, the perforators that cut them, and the premises
these give for dating a roll. The site is at https://pfefferniels.github.io/condon-dates/.

## Contents

| Path | Content |
|---|---|
| `data/readings.json` | what was read off each roll, keyed by druid. Corrections go here and nowhere else |
| `hands.json` | the signature clusters |
| `dates/` | the search of every scan for its punch date ([README](dates/README.md)) |
| `perforator/` | chain pitch and advance, measured on every scan ([README](perforator/README.md)) |
| `paper/` | colour and ruling of the paper ([README](paper/README.md)) |
| `review/` | the page the date candidates were reviewed on |
| `docs/` | the site, served by GitHub Pages |
| `w3id/condon-welte/` | the redirects for the IRIs below |

`dates/`, `perforator/` and `paper/` came here from punch-225 in welte225.org on 26 September
2026, whose history holds how they came about.

## Build

    python3 build.py

This writes the trimmed views in `data/`, the site data in `docs/data/` and the linked data.
The premises link `premises.py` at the commit the checkout stands at, so commit a change to
it before building.

## Linked data

Under `https://w3id.org/condon-welte/`, in the format of
[linked-rolls](https://github.com/pfefferniels/linked-rolls), CC BY 4.0.

| IRI | File | Content |
|---|---|---|
| `premises#<id>` | `docs/premises.jsonld` | the premises |
| `papers#<id>` | `docs/papers.jsonld` | the classes of paper |
| `hands/<id>` | `docs/hands.jsonld` | the hands, as authority records |
| `evidence/<name>` | `docs/evidence/<name>.json` | the dated copies a premise rests on |
| `context.jsonld` | `docs/context.jsonld` | the terms linked-rolls does not have yet |

A browser is sent to `docs/premises.html` or to the hand on the front page, any other client
to the JSON-LD. The prefix is not registered yet.

- **Premises.** A premise states that a setting of the perforator or a class of paper was
  used only before a day, after one, or between two. An edition measures its own copy and
  cites the premise that dates it. `premises.html` gives each premise with its reasons.
- **Bounds.** A bound rests on the dated copy at its edge, so that copy's reading must be
  graded high or verified on the scan (`verified` in `data/readings.json`). Otherwise the
  premise is held possible at most, and the build lists the copy to read again. Every build
  works the bounds out anew and keeps the IRIs, so an edition should cite the commit.
- **Hands.** A hand is a person known by a signature, the one thing about these rolls no
  authority file holds. An edition names it as the actor of an inscription. An id is kept
  once published, even where the name read off the signature changes. Everything else, the
  company for one, is named by the GND.
