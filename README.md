# Condon Welte rolls: dates and hands

A small static page showing when the red Welte rolls of the Condon collection at Stanford
were punched, and the hands that signed them. It is an overview, not an argument: a bar
chart of rolls per year, one number for how many can be dated at all, and a registry of the
signing hands.

The page is in `docs/` and is served by GitHub Pages. Images are hot-linked from Stanford's
IIIF endpoint; nothing is bundled.

## Data

`docs/data/rolls.json` is generated, never edited by hand. It comes from the dating run in

    ../welte225.org/punch-225/dates/candidates.json

which belongs to another working copy and is read-only here. Regenerate with:

    python3 build.py

Every roll with a `date_iso` counts as dated, whatever its confidence. Confidence appears
nowhere on the page and is not used as a filter.

One trap worth recording: `read_region` is 1-based into the `regions` array **in the order
the file lists it**, not in order of score. Sorting the regions first shows the wrong crop
on about a quarter of the rolls. A letter prefix (`e1`, `w1`) selects that region's wider
`view_e` / `view_w` box.

## The registry

`hands.json` is the one hand-made file. It groups signatures into clusters by how they look.
The `hand` field transcribed in `candidates.json` was used only as corroboration, because
the transcriptions are guesses at illegible hands and both split one person and merge two:

- The short countersignature transcribed *Wössler* on the 1910–11 rolls is a different hand
  from the long *Wissler* of 1911–13. They are kept apart (Controllers 1 and 6).
- *Hohnrich*, *Hohmüller*, *Hohnreich* and *Hohn* are one hand, kept together (Controller 7).
- Five rolls transcribed only as an illegible word carry the same *Kopf* signature
  (Controller 4), and one transcribed as an illegible name is *Fritz* (Controller 2).

Clusters of two or more rolls are numbered `Controller 1, 2, 3 …` by how often they appear.
Hands seen only once are shown at the end without a number, since a single specimen is not
enough to say it is distinct from the rest.

The term *controller* follows the edition, which reads roll 225's
`225. Fritz. 18 Jan 09.` as a mark whose purpose is control.

## Layout

    build.py        regenerates docs/data/rolls.json
    hands.json      the signature clustering, made by looking
    docs/           what GitHub Pages serves
      index.html
      style.css
      app.js
      data/rolls.json
