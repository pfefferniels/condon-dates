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
`paper/` measures the paper on the scans themselves: `paper/colour.json` holds the colour
of each roll's paper, corrected against the grey card scanned above its leader (see
`paper/README.md`). `build.py` turns them into `docs/data/rolls.json` and the linked data
below.

## Premises

The measurements are published not roll by roll but as premises for dating a roll: what
measuring all of them allows an edition to conclude about any one. An edition measures
its own copy and states that measurement itself, and names a premise from here in the
inference that dates the copy, so it stays whole on its own and each document reasons
about what it owns. The premises are in the format of
[linked-rolls](https://github.com/pfefferniels/linked-rolls): each is a production that
stands for many copies, "the red rolls punched with an advance of 1.0 mm", and its date
carries the belief an edition names, with the dated copies, the data and the scripts it
rests on.

| File | IRI | Content |
|---|---|---|
| `docs/premises.jsonld` | `https://w3id.org/welte-premises/premises` | the premises |
| `docs/papers.jsonld` | `https://w3id.org/welte-premises/papers#<id>` | the classes of paper the premises name |
| `docs/evidence/<name>.json` | `https://w3id.org/welte-premises/evidence/<name>` | the copies a premise rests on |
| `docs/premises.html` | | the page a browser following a premise IRI is shown |
| `docs/context.jsonld` | `https://w3id.org/welte-premises/context.jsonld` | the terms linked-rolls does not have yet |
| `docs/hands.jsonld` | `https://w3id.org/welte-hands/<id>` | the hands, as authority records |

Seven premises stand. Two are on the advance, the one quantity of the perforator that
punch-225 found to date a roll; the punch and the pitch say which machine cut it, not when.
`premises#advance-1mm-belief` holds that the 1.0 mm advance was not used after the day of
the first dated copy with the late one, and `premises#advance-half-mm-belief` that the
0.5 mm advance was not used before the day of the last dated copy with the early one.

Five are on the paper, by its colour. Four kinds are told apart: warm red, cool red, buff
and green, each defined in `docs/papers.jsonld` by a rule on the corrected colour. Cool
red, buff and green were punched on the narrow perforator alone, warm red on both, so a
kind says something of the machine as well as of the time. Two narrower classes, a bright
warm red and a light cool red, are dated closer together than random groups of their kind
allow, and are taken for stocks or batches of paper. Each premise states the window its
dated copies span: cool red not before 24 August 1911, bright warm red between November
1923 and November 1925, light cool red between October 1921 and February 1922, buff between
November 1919 and July 1922, green between January 1918 and November 1922. A class attested
on few dated copies is held possible, and the reasons of every paper premise say how many
copies it rests on, whether the dates are closer than chance, and which dated copies lie
just outside the rule's edge, so that a reader sees what the rule decides. A dated copy of
a class that falls outside its window is worth reading again: Welte 292 was, and was
misread.

The counts, the bounds and the copies each bound rests on are worked out from
`data/readings.json`, `data/perforator.json` and `paper/colour.json` on every build, so a
corrected reading moves the premise and not its IRI. An edition should record the commit of the premise it
cites. The premises link `premises.py` at the commit the checkout stands at, so build after
committing a change to it.

The hands are not premises but identities, and the one thing about these rolls no
authority file holds. An edition names one as the actor of the act that wrote an
inscription, e.g. `https://w3id.org/welte-hands/fritz`, and takes nothing from it to date
a copy: the hand and the date come off the same inscription. They stand under a prefix of
their own, since an identity should outlast the evidence that moves a premise, and an id
is kept once published even where the name read off the signature changes. Everything
else is named by the GND: the premises name the company as
[M. Welte & Söhne](https://d-nb.info/gnd/5125268-5).

`docs/premises.html` shows each premise with the belief, its reasons and what it rests on,
and the evidence as a timeline of the dated copies with the bound of each premise marked,
every copy linked to its scan at Stanford. w3id sends a browser that follows a premise IRI
there, and one that follows a hand's IRI to the hand's signatures on the main page; any
other client is given the JSON-LD.

The data are published under CC BY 4.0. Neither prefix, nor `w3id.org/reo`, whose context
the documents name, is registered yet: `w3id/welte-premises/` and `w3id/welte-hands/` are
the folders to submit to [perma-id/w3id.org](https://github.com/perma-id/w3id.org).
