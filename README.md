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

`data/catalogue.json` holds what Stanford catalogues about each roll and whether it has a
scan, and is refreshed from punch-225 with `sync.py`. `hands.json` holds the signature
clusters. `build.py` turns the three into `docs/data/rolls.json`.
