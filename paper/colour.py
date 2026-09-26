#!/usr/bin/env python3
"""Measure the colour of the paper of every scanned roll, and of the grey card scanned with it.

    python3 paper/colour.py [druid ...]

The colour of a roll's paper is evidence for the stock it was cut from, and so for when it
was punched. It is measured here from Stanford's scans, as the scanner saw it, and written
to paper/colour.json; how the stocks are told apart is decided elsewhere.

The paper is measured in WINDOWS windows spread evenly between the first and the last
hole, each across the width of the paper, less a margin at either edge, and WINDOW_ROWS
rows along it, fetched at 1/SHRINK so that the server averages the grain away. In a window
the holes, where the scanner's white backing shows through, are the pixels at or near
white; ruling lines, ink, fibre specks and stains are darker than the paper. Both are
dropped by keeping only the pixels whose luminance lies within BAND standard deviations
of its mode, the width taken from the half width of the peak, and the window's colour is
the median sRGB of what is left. The roll's colour is the median of its windows in
CIELAB (sRGB companding, D65 white); its spread is their interquartile range; its trend
is the median of the windows in the first quarter of the roll, the outer wraps next to
the leader that have seen the most light, less that of the last quarter, next to the core.

Every scan also has a QPcard 101 hanging above the tip of its leader, with a black, a
dark grey and a white patch, the only neutral reference inside the scan. It is looked for
in the first TOP_ROWS rows at 1/TOP_SHRINK, as the tallest block of wide dark neutral rows,
then followed down its middle as three flat neutral runs of rising lightness. The middle of
each patch is measured at full resolution: its median sRGB and how much of it the scanner
clipped at 255. A patch channel clipped in CLIPPED or more of its pixels is not used, since
its median is no longer the patch. The card's nominal values cannot be checked here, so the
correction is relative: for each channel, in linear light, the gain and offset that best map
a scan's patches onto the median patches of the corpus, one scanner, are applied to its
paper, and the paper is reported both raw and corrected.

Every download is cached in paper/cache/ by its URL, so a rerun fetches nothing. No more
than WORKERS requests are made at once, and a failed one is retried with a growing pause.
Given druids, only those rolls are measured, against the reference card of the last full
run where there is one, and the result is printed, not written.
"""
import hashlib
import http.client
import json
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).parent
CATALOGUE = HERE.parent / "data" / "catalogue.json"
CACHE = HERE / "cache"
TARGET = HERE / "colour.json"
IIIF = "https://stacks.stanford.edu/image/iiif/{druid}%2F{druid}_0001"

WORKERS = 6            # requests at once; the server is shared
TRIES = 6              # attempts at a request, the pause doubling from 3 s
WINDOWS = 16           # paper windows between the first and the last hole
WINDOW_ROWS = 400      # rows of a window, 1.3 in
MARGIN = 60            # columns left off either edge of the paper
SHRINK = 4             # windows are fetched at 1/4
BAND = 2.5             # paper lies within this many standard deviations of the mode
LEAST_PAPER = 0.25     # a window with less of its pixels kept as paper is not used
TOP_ROWS = 6000        # the card hangs within these rows
TOP_SHRINK = 8         # and is looked for at 1/8
INSET = 0.2            # of a patch's width and height left off each side when it is measured
CLIPPED = 0.4          # a patch channel clipped in this much of its pixels is not used
PATCHES = ("black", "grey", "white")

LUMA = np.array([0.2126, 0.7152, 0.0722])
SRGB_TO_XYZ = np.array([[0.4124, 0.3576, 0.1805],
                        [0.2126, 0.7152, 0.0722],
                        [0.0193, 0.1192, 0.9505]])
D65 = SRGB_TO_XYZ.sum(1)


def fetch(url):
    """The body of url, from the cache when it has been fetched before."""
    path = CACHE / (hashlib.sha1(url.encode()).hexdigest() + Path(url).suffix)
    if path.exists():
        return path.read_bytes()
    for attempt in range(TRIES):
        try:
            with urllib.request.urlopen(url, timeout=180) as response:
                data = response.read()
            break
        except (OSError, http.client.HTTPException) as error:
            code = getattr(error, "code", None)
            if attempt == TRIES - 1 or (code and code < 500 and code != 429):
                raise
            time.sleep(3 * 2 ** attempt)
    CACHE.mkdir(parents=True, exist_ok=True)
    part = path.with_suffix(".part")
    part.write_bytes(data)
    part.replace(path)
    return data


def image(druid, region, size="full"):
    url = f"{IIIF.format(druid=druid)}/{region}/{size}/0/default.png"
    return np.asarray(Image.open(BytesIO(fetch(url))).convert("RGB"))


def linear(rgb):
    c = np.asarray(rgb, float) / 255
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def encoded(lin):
    c = np.clip(lin, 0, 1)
    return 255 * np.where(c <= 0.0031308, 12.92 * c, 1.055 * c ** (1 / 2.4) - 0.055)


def lab(rgb):
    """CIELAB of sRGB values (0-255, last axis the channel), D65 white."""
    xyz = linear(rgb) @ SRGB_TO_XYZ.T / D65
    f = np.where(xyz > (6 / 29) ** 3, np.cbrt(xyz), xyz / (3 * (6 / 29) ** 2) + 4 / 29)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]),
                     200 * (f[..., 1] - f[..., 2])], -1)


def runs(mask):
    """(start, end) of the runs of True in a 1-d mask, end exclusive."""
    edges = np.diff(np.r_[0, mask.astype(int), 0])
    return list(zip(np.nonzero(edges == 1)[0].tolist(), np.nonzero(edges == -1)[0].tolist()))


def find_card(top):
    """Columns and the row runs of the black, grey and white patch in an overview, or None."""
    top = top.astype(float)
    dark = (top.mean(2) < 70) & (np.ptp(top, 2) < 16)
    spans = {}
    for y, row in enumerate(dark):
        wide = [r for r in runs(row) if r[1] - r[0] >= 30]
        if wide:
            spans[y] = max(wide, key=lambda r: r[1] - r[0])
    blocks = []
    for y in sorted(spans):          # the white line between black and grey is bridged
        if blocks and y - blocks[-1][-1] <= 8:
            blocks[-1].append(y)
        else:
            blocks.append([y])
    if not blocks:
        return None
    block = max(blocks, key=len)
    x0 = int(np.median([spans[y][0] for y in block]))
    x1 = int(np.median([spans[y][1] for y in block]))
    inset = (x1 - x0) // 5
    middle = top[:, x0 + inset:x1 - inset]
    level = np.median(middle.mean(2), 1)
    flat = (middle.mean(2).std(1) < 8) & (np.median(np.ptp(middle, 2), 1) < 16) & (level < 253)
    steps = []                       # flat runs of one lightness, at least 12 rows long
    for s, e in runs(flat):
        start = s
        for y in range(s + 1, e + 1):
            if y == e or abs(level[y] - np.median(level[start:y])) > 8:
                if y - start >= 12:
                    steps.append((start, y, float(np.median(level[start:y]))))
                start = y
    for (b0, b1, black), (g0, g1, grey), (w0, w1, white) in zip(steps, steps[1:], steps[2:]):
        if black < grey - 6 and grey < 120 and white > grey + 60 and g0 - b1 < 16 and w0 - g1 < 16:
            return (x0, x1), [(b0, b1), (g0, g1), (w0, w1)]
    return None


def measure_card(druid, width, height):
    rows = min(TOP_ROWS, height)
    top = image(druid, f"0,0,{width},{rows}", f"{width // TOP_SHRINK},")
    found = find_card(top)
    if not found:
        return None
    sx, sy = width / top.shape[1], rows / top.shape[0]
    (x0, x1), steps = found
    inset = INSET * (x1 - x0)
    cols = round((x0 + inset) * sx), round((x1 - inset) * sx)
    card = {"at": [round(x0 * sx), round(steps[0][0] * sy), round((x1 - x0) * sx),
                   round((steps[2][1] - steps[0][0]) * sy)], "clip": {}}
    for name, (y0, y1) in zip(PATCHES, steps):
        pad = INSET * (y1 - y0)
        top_row, bottom_row = round((y0 + pad) * sy), round((y1 - pad) * sy)
        patch = image(druid, f"{cols[0]},{top_row},{cols[1] - cols[0]},{bottom_row - top_row}")
        px = patch.reshape(-1, 3)
        card[name] = np.median(px, 0).round(1).tolist()
        card["clip"][name] = (px >= 255).mean(0).round(3).tolist()
    return card


def paper_colour(window):
    """Median sRGB of the pixels of a window near its luminance mode, and their share."""
    px = window.reshape(-1, 3).astype(float)
    luma = px @ LUMA
    shut = px.max(1) < 250           # holes and anything clipped are out
    counts = np.convolve(np.histogram(luma[shut], 256, (0, 256))[0], np.ones(5) / 5, "same")
    mode = int(counts.argmax())
    below = np.nonzero(counts[:mode] <= counts[mode] / 2)[0]
    above = np.nonzero(counts[mode:] <= counts[mode] / 2)[0]
    half = min(mode - below[-1] if len(below) else 256, above[0] if len(above) else 256)
    sigma = max(half / 1.1774, 1.0)
    keep = shut & (np.abs(luma - mode) <= BAND * sigma)
    if not keep.any():
        return None, 0.0
    return np.median(px[keep], 0), float(keep.mean())


def measure(roll):
    druid = roll["druid"]
    info = json.loads(fetch(f"{IIIF.format(druid=druid)}/info.json"))
    width, height = info["width"], info["height"]
    problems = []
    card = measure_card(druid, width, height)
    if not card:
        problems.append("no card found in the first rows")
    x0, x1 = roll["paper"][0] + MARGIN, roll["paper"][1] - MARGIN
    first, last = roll["holes"]
    windows = []
    for i in range(WINDOWS):
        y = round(first + (i + 0.5) * (last - first) / WINDOWS - WINDOW_ROWS / 2)
        rgb, share = paper_colour(image(druid, f"{x0},{y},{x1 - x0},{WINDOW_ROWS}", f"pct:{100 / SHRINK:g}"))
        if share < LEAST_PAPER:
            problems.append(f"window at row {y}: only {share:.0%} of it kept as paper")
            windows.append([y, None, None, None, round(share, 2)])
        else:
            windows.append([y, *np.round(rgb, 1).tolist(), round(share, 2)])
    return {"welte": roll["welte_number"], "card": card,
            "windows": windows, "problems": problems}


def fit(card, reference):
    """Per channel, gain and offset in linear light taking a card's patches to the reference's."""
    fitted = []
    for c in range(3):
        used = [p for p in PATCHES if card["clip"][p][c] < CLIPPED]
        if len(used) < 2:
            return None
        x = linear([card[p][c] for p in used])
        y = linear([reference[p][c] for p in used])
        fitted.append(np.polyfit(x, y, 1).tolist())
    return fitted


def summary(rgbs, index):
    """Median, interquartile range and outer-less-inner trend of a roll's windows in L*a*b*."""
    labs = lab(np.array(rgbs))
    q1, q3 = np.percentile(labs, [25, 75], 0)
    outer = labs[index < WINDOWS // 4]
    inner = labs[index >= WINDOWS - WINDOWS // 4]
    trend = (np.median(outer, 0) - np.median(inner, 0)).round(1).tolist() if len(outer) and len(inner) else None
    return {"rgb": np.median(rgbs, 0).round(1).tolist(), "lab": np.median(labs, 0).round(1).tolist(),
            "iqr": (q3 - q1).round(1).tolist(), "trend": trend}


def finish(entry, reference):
    """Add the correction and the raw and corrected colour of the paper to a measured roll."""
    used = [(i, w[1:4]) for i, w in enumerate(entry["windows"]) if w[1] is not None]
    entry["n"] = len(used)
    entry["correction"] = entry["card"] and fit(entry["card"], reference)
    if entry["card"] and not entry["correction"]:
        entry["problems"].append("card clipped in two of its patches; not corrected")
    if not used:
        entry["problems"].append("no usable paper window")
        return entry
    index = np.array([i for i, _ in used])
    raw = np.array([rgb for _, rgb in used])
    entry["raw"] = summary(raw, index)
    if entry["correction"]:
        gain, offset = np.array(entry["correction"]).T
        entry["corrected"] = summary(encoded(linear(raw) * gain + offset), index)
        entry["correction"] = [[round(g, 4), round(o, 5)] for g, o in entry["correction"]]
    return entry


def main():
    rolls = [r for r in json.loads(CATALOGUE.read_text()) if r["scanned"]]
    if sys.argv[1:]:
        rolls = [r for r in rolls if r["druid"] in sys.argv[1:]]
    done = 0

    def attempt(roll):
        nonlocal done
        try:
            entry = measure(roll)
        except Exception as error:
            entry = {"welte": roll["welte_number"], "card": None, "windows": [],
                     "problems": [f"not measured: {type(error).__name__}: {error}"]}
        done += 1
        if done % 25 == 0:
            print(f"{done}/{len(rolls)}", flush=True)
        return roll["druid"], entry

    with ThreadPoolExecutor(WORKERS) as pool:
        measured = dict(pool.map(attempt, rolls))

    corpus = json.loads(TARGET.read_text()) if sys.argv[1:] and TARGET.exists() else measured
    cards = [e["card"] for e in corpus.values() if e["card"]]
    reference = {p: np.median([c[p] for c in cards], 0) for p in PATCHES}
    result = {druid: finish(entry, reference) for druid, entry in sorted(measured.items())}

    found = sum(1 for e in result.values() if e["card"])
    corrected = sum(1 for e in result.values() if e.get("corrected"))
    print("reference card", {p: v.round(1).tolist() for p, v in reference.items()})
    print(f"{len(result)} rolls, {found} cards found, {corrected} corrected, "
          f"{sum(1 for e in result.values() if e['problems'])} with problems")
    if sys.argv[1:]:
        for druid, entry in result.items():
            print(druid, json.dumps({k: entry.get(k) for k in ("welte", "card", "correction", "n", "raw",
                                                               "corrected", "problems")}))
        return
    TARGET.write_text(json.dumps(result, separators=(",", ":")))
    print(f"wrote {TARGET.relative_to(HERE.parent)} ({TARGET.stat().st_size // 1024} kB)")


if __name__ == "__main__":
    main()
