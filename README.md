# Dates, Hands, Paper and Perforators of Condon Welte Rolls

A small static site on the red Welte rolls of the Condon collection at Stanford: when they
were punched, the hands that signed them, the paper they were cut on and the perforators
that cut them, and the premises these give for dating a roll.

The site is in `docs/` and is served by GitHub Pages. The front page shows each of these in
a section of its own, with the data behind it: the dates by year, the hands with their
signatures, the classes of paper with every roll in the colour of its paper, the chain pitch
and the advance of the perforator against the date, and the premises. `premises.html` states
each premise in full and is where a premise's IRI leads. Both draw their charts with
`docs/charts.js`, and every chart has its values in a table beside it. Images are
hot-linked from Stanford's IIIF endpoint; nothing is bundled.

## Data

Everything measured or read on these rolls is kept here, each thing once.

`data/readings.json` is the record of what was read off each roll, keyed by druid: the
inscription, the date as written and as ISO, its confidence, the written roll number, the
hand, the reader's notes and the IIIF crop the reading was made from. Corrections are made
there and nowhere else. `source` names the file in `dates/readings/` each reading came from,
or `authoritative.json` for one the editor read again on the scan.

| Directory | Content |
|---|---|
| `dates/` | the search of every scan for its punch date: the index of the rolls (`candidates.json`), the crops, what the readers were told and what they wrote (see `dates/README.md`) |
| `perforator/` | the perforator measured on every scan: the chain pitch (`pitch.json`), the advance (`step.json`), the corpus check and the libraries that take a perforation apart (see `perforator/README.md`) |
| `paper/` | the paper measured on every scan: its colour against the grey card, and its ruling (see `paper/README.md`) |
| `review/` | the page the date candidates were reviewed on |

These moved here from `punch-225` in welte225.org on 26 September 2026, whose history holds
how they came about; punch-225 keeps only the measurement of the copies of WM 225 and takes
its libraries and sweeps from here. `hands.json` holds the signature clusters.

`build.py` writes `data/catalogue.json`, what Stanford catalogues about each roll, whether it
has a scan and where the paper lies in it, and `data/perforator.json`, each roll's row of the
two sweeps, as trimmed views the other scripts read; they are not edited. It then turns all
of it into `docs/data/rolls.json`, `docs/data/measures.json` and the linked data below.

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

Eight premises stand. Two are on the advance, the one quantity of the perforator that
the study in `perforator/` found to date a roll; the punch and the pitch say which machine
cut it, not when.
`premises#advance-1mm-belief` holds that the 1.0 mm advance was not used after the day of
the first dated copy with the late one, and `premises#advance-half-mm-belief` that the
0.5 mm advance was not used before the day of the last dated copy with the early one.

Five are on the paper, by its colour. Four kinds are told apart: warm red, cool red, buff
and green, each defined in `docs/papers.jsonld` by a rule on the corrected colour. Cool
red, buff and green were punched on the narrow perforator alone, warm red on both, so a
kind says something of the machine as well as of the time. Two narrower classes, a bright
warm red and a light cool red, are dated closer together than random groups of their kind
allow, and are taken for stocks or batches of paper. Each premise states the window its
dated copies span: cool red not before 19 August 1914, bright warm red between November
1923 and November 1925, light cool red between October 1921 and February 1922, buff between
November 1919 and July 1922, green between January 1918 and November 1922. Ruled paper, printed
with a line along each track, is a class of its own, found by `paper/ruling.py`: 30 rolls,
all warm red and all cut on the wide perforator, and the premise holds that it was not used
after the last of them, 1 February 1910. A class attested
on few dated copies is held possible, and the reasons of every paper premise say how many
copies it rests on, whether the dates are closer than chance, and which dated copies lie
just outside the rule's edge, so that a reader sees what the rule decides. A dated copy of
a class that falls outside its window is worth reading again: Welte 292 and Welte 1534
were, and both were misread, the one as 1914 for 1924, the other as 1916 for 1910.

The counts, the bounds and the copies each bound rests on are worked out from
`data/readings.json`, `data/perforator.json`, `paper/colour.json` and `paper/ruling.json` on
every build, so a
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
