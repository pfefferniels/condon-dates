# The paper, measured on the scans

The paper a roll was cut on is evidence for when it was punched, and for which perforator
punched it. These scripts measure it on Stanford's scans; `premises.py` turns what they find
into classes of paper and premises.

`colour.py` takes the colour of the blank paper in sixteen windows along each roll, keeping
the pixels near the mode of their lightness so that holes, ruling, ink and specks drop out,
and corrects it against the QPcard 101 grey card that hangs above the leader of every scan.
The correction is needed: the scans were exposed differently, and St1's card reads 190 on
its white patch where most read about 245, which uncorrected would pass for darker paper.
It is relative, mapping each scan's card onto the median card of the corpus, since the
card's nominal values cannot be checked here. The card is found on 447 of the 454 scans;
within a roll the corrected colour varies by less than one unit of L*, a* or b*. Writes
`colour.json`.

`ruling.py` looks for the fine dark lines some red paper is printed with, one along each
track, as the periodic component of the paper's profile across the roll at the track pitch,
and compares their phase with that of the holes. The strengths fall in two groups with
nothing between 2 and 25: 30 rolls are ruled, 421 are not, 3 are uncertain. Every ruled roll
is warm red, was cut on the wide perforator, and has its lines on the track centres at
3.198 mm; its dated copies run from January 1907 to February 1910. Writes `ruling.json`.

    python3 paper/colour.py [druid ...]
    python3 paper/ruling.py [druid ...]

Both cache every download in `paper/cache/`, which is not committed, and need numpy, Pillow
and the network.
