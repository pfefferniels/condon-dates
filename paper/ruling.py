#!/usr/bin/env python3
"""Whether the paper of each scanned roll is ruled.

Some red rolls are cut from paper printed with fine dark lines running along the roll,
one line per track. On the scans such a line is three or four pixels wide and a few grey
levels to a few tens darker than the paper around it, and it runs unbroken over the whole
width and length, through the bridges between the holes of a track. The pattern is
periodic at the track pitch, which perforator/pitch.py measured on every scan (the Teilung of
data/perforator.json), so it is looked for at that period and nowhere else.

For each roll, twelve windows are spread evenly between the first and the last hole. Each
is a strip 1024 rows long across the paper, fetched from Stanford's IIIF server in grey at
full resolution across the roll and shrunk eight times along it, which averages the rows
without blurring a line that runs along them. The holes, where the white backing shows,
are masked with a margin; the median down each column over what remains gives the paper's
profile across the roll, and subtracting a running median of 15 columns keeps the narrow
lines and drops the broad shading. The Fourier projection of that profile at the track
pitch measures the ruling; its strength is its amplitude over the median amplitude at
periods away from the pitch (24 to 56 px, more than 2.5 px from it), so a strength near 1
is paper without lines. A search over periods near the pitch confirms that the peak lies
at the pitch and not merely near it. The phase of the lines is compared with the phase of
the holes in the same window, which sit on the track centres, so that a ruling on the
tracks reads 0 and one between them 0.5 of a pitch. A scanner artefact would sit at fixed
image columns and not follow the holes from roll to roll.

A roll is called ruled when the median strength over its windows reaches RULED, not ruled
when it stays below PLAIN, and uncertain between them, or where its windows disagree
(some ruled, some not). The two thresholds sit in the empty gap of the distribution of
strengths over all rolls, which ruling.md shows. Secondary, and not used for the call: the
density of small dark specks on one full-resolution tile per roll, which is high on
fibrous buff paper.

    python3 paper/ruling.py [druid ...]

Downloads are cached under paper/cache/ by URL, so a rerun costs nothing. Writes
paper/ruling.json, keyed by druid; a roll that could not be measured carries `problems`.
"""
import json
import re
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
ROOT = HERE.parent
CATALOGUE = ROOT / "data" / "catalogue.json"
PERFORATOR = ROOT / "data" / "perforator.json"
CACHE = HERE / "cache"
TARGET = HERE / "ruling.json"

STACKS = "https://stacks.stanford.edu/image/iiif"
DPI, MM_PER_INCH = 300.25, 25.4
TEILUNG = 3.195                 # mm, the median track pitch of the red rolls, where a scan gives none
WINDOWS, ROWS, SHRINK = 12, 1024, 8
MARGIN = 20                     # px left out at each paper edge
DETREND = 7                     # half-width of the running median, px
OFF = (24, 56, 2.5)             # off-periods: range in px, and how far from the pitch
SEARCH = 3.0                    # px either side of the pitch searched for the peak
WORKERS, TRIES = 6, 5
HOLE_COLUMNS = 60               # columns with a hole needed to fix the track grid (about three holes)
DIP = 3.0                       # grey levels below the running median that make a line

RULED, PLAIN = 4.0, 2.0         # median strength: ruled at or above, plain below


def fetch(url):
    """The bytes at url, from the cache or from Stanford, with retries and backoff."""
    path = CACHE / re.sub(r"[^\w.,!-]+", "_", url.split("/iiif/")[1])
    if path.exists():
        return path.read_bytes()
    for attempt in range(TRIES):
        try:
            with urllib.request.urlopen(url, timeout=120) as response:
                data = response.read()
            CACHE.mkdir(parents=True, exist_ok=True)
            part = path.with_suffix(".part")
            part.write_bytes(data)
            part.rename(path)
            return data
        except urllib.error.HTTPError as error:
            if error.code < 500 and error.code != 429 or attempt == TRIES - 1:
                raise
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if attempt == TRIES - 1:
                raise
        time.sleep(2 ** attempt * 3)


def image(druid, region, size="full"):
    url = f"{STACKS}/{druid}%2F{druid}_0001/{region}/{size}/0/gray.png"
    return np.asarray(Image.open(BytesIO(fetch(url))).convert("L"), dtype=float)


def dilate(mask, dy, dx):
    padded = np.pad(mask, ((dy, dy), (dx, dx)))
    out = np.zeros_like(mask)
    for i in range(2 * dy + 1):
        for j in range(2 * dx + 1):
            out |= padded[i:i + mask.shape[0], j:j + mask.shape[1]]
    return out


def running_median(p, half):
    padded = np.pad(p, half, mode="edge")
    return np.median(np.lib.stride_tricks.sliding_window_view(padded, 2 * half + 1), axis=1)


def projection(signal, x, periods):
    """Fourier coefficient of signal (sampled at columns x) at each period."""
    periods = np.atleast_1d(periods)
    return (np.exp(-2j * np.pi * np.outer(1 / periods, x)) @ signal) * 2 / len(x)


def phase(coefficient, pitch):
    """The column, modulo the pitch, at which a pattern with this coefficient peaks."""
    return (-np.angle(coefficient) / (2 * np.pi) * pitch) % pitch


def window(strip, x0, pitch):
    """Measure one strip: its paper profile, the ruling at the pitch, the hole grid."""
    paper = np.median(strip)
    if paper > 200:
        return None                             # backing, not paper: past the end of a fragment
    holes = strip > paper + 0.25 * (255 - paper)
    kept = np.where(dilate(holes, 1, 3), np.nan, strip)
    enough = np.sum(~np.isnan(kept), axis=0) >= strip.shape[0] // 8
    profile = np.full(strip.shape[1], np.nan)
    profile[enough] = np.nanmedian(kept[:, enough], axis=0)
    x = np.arange(strip.shape[1])
    filled = np.interp(x, x[enough], profile[enough])
    lines = np.where(enough, filled - running_median(filled, DETREND), 0.0)
    x = x + x0                                  # image columns, so phases compare across windows

    periods = np.arange(OFF[0], OFF[1], 0.05)
    spectrum = np.abs(projection(lines, x, periods))
    noise = np.median(spectrum[np.abs(periods - pitch) > OFF[2]])
    at = projection(-lines, x, pitch)[0]        # dark lines as peaks
    near = np.abs(periods - pitch) <= SEARCH
    peak = periods[near][np.argmax(spectrum[near])]

    grid = holes.mean(axis=0)
    at_holes = projection(grid, x, pitch)[0]
    locked = abs(at_holes) / max(grid.mean() * 2, 1e-9)   # about 0.45 for round holes on the grid
    offset = None
    if (grid > 0).sum() >= HOLE_COLUMNS and locked > 0.25:
        offset = ((phase(at, pitch) - phase(at_holes, pitch)) / pitch + 0.5) % 1 - 0.5

    # Any long dark line, at whatever spacing: a local minimum of the profile at least
    # DIP grey levels deep. Ruling gives one per track, hand-drawn guide lines fewer.
    deep = (lines < -DIP) & (lines <= np.roll(lines, 1)) & (lines <= np.roll(lines, -1))
    dips = x[deep]
    return {"strength": abs(at) / noise, "amplitude": abs(at), "peak": peak,
            "offset": offset, "paper": paper, "dips": dips}


def circular(offsets):
    """Mean of offsets in pitches (-0.5..0.5) and the length of their resultant (0..1)."""
    z = np.mean(np.exp(2j * np.pi * np.asarray(offsets)))
    return float(np.angle(z) / (2 * np.pi)), float(abs(z))


def specks(druid, roll):
    """Secondary: small dark specks per cm² on one full-resolution tile mid-roll."""
    (a, b), (h0, h1) = roll["paper"], roll["holes"]
    tile = image(druid, f"{(a + b) // 2 - 512},{(h0 + h1) // 2 - 512},1024,1024")
    paper = np.median(tile)
    holes = dilate(tile > paper + 0.25 * (255 - paper), 4, 4)
    blocks = tile.reshape(32, 32, 32, 32).transpose(0, 2, 1, 3).reshape(32, 32, -1)
    background = np.repeat(np.repeat(np.median(blocks, axis=2), 32, 0), 32, 1)
    dark = (tile < background * 0.8) & ~holes
    area = (~holes).sum() / (DPI / 2.54) ** 2
    return round(float(dark.sum() / area), 1)


def measure(roll, pitch_mm):
    druid = roll["druid"]
    pitch = pitch_mm / MM_PER_INCH * DPI
    (a, b), (h0, h1) = roll["paper"], roll["holes"]
    x0, width = a + MARGIN, b - a - 2 * MARGIN
    windows, problems = [], []
    for k in range(WINDOWS):
        y = int(h0 + (k + 0.5) / WINDOWS * (h1 - h0)) - ROWS // 2
        try:
            strip = image(druid, f"{x0},{y},{width},{ROWS}", f"{width},{ROWS // SHRINK}")
        except Exception as error:                  # noqa: BLE001 - recorded, not fatal
            problems.append(f"window {k} at y={y}: {error}")
            continue
        measured = window(strip, x0, pitch)
        if measured is None:
            problems.append(f"window {k} at y={y}: no paper")
        else:
            windows.append(measured)
    result = {"pitch_px": round(pitch, 2)}
    if problems:
        result["problems"] = problems
    if len(windows) < WINDOWS // 2:
        result["call"] = "failed"
        return result

    strength = np.array([w["strength"] for w in windows])
    median = float(np.median(strength))
    ruled = strength >= RULED
    mixed = ruled.any() and (strength < PLAIN).any()
    call = ("uncertain" if mixed else
            "ruled" if median >= RULED else "no" if median < PLAIN else "uncertain")
    result.update({
        "call": call,
        "strength": round(median, 1),
        "range": [round(float(strength.min()), 1), round(float(strength.max()), 1)],
        "ruled_windows": f"{int(ruled.sum())}/{len(windows)}",
        "amplitude": round(float(np.median([w["amplitude"] for w in windows])), 2),
        "paper_grey": round(float(np.median([w["paper"] for w in windows]))),
    })
    chosen = [w for w, r in zip(windows, ruled) if r]
    if chosen:
        period = float(np.median([w["peak"] for w in chosen]))
        result.update({"period_px": round(period, 2),
                       "period_mm": round(period / DPI * MM_PER_INCH, 3),
                       "period_off_pitch": round(period / pitch - 1, 4)})
    offsets = [w["offset"] for w in chosen if w["offset"] is not None]
    if offsets:
        mean, consistency = circular(offsets)
        result.update({"offset": round(mean, 2), "consistency": round(consistency, 2),
                       "lies": "on tracks" if abs(mean) < 0.25 else "between tracks"})
    counts = [len(w["dips"]) for w in windows]
    gaps = np.concatenate([np.diff(w["dips"]) for w in windows])
    result["lines"] = int(np.median(counts))
    if result["lines"] >= 3:
        result["line_spacing"] = round(float(np.median(gaps)) / pitch, 2)
    try:
        result["specks_per_cm2"] = specks(druid, roll)
    except Exception as error:                      # noqa: BLE001
        result.setdefault("problems", []).append(f"specks: {error}")
    return result


def main():
    rolls = [r for r in json.loads(CATALOGUE.read_text()) if r["scanned"]]
    measured = json.loads(PERFORATOR.read_text())["rolls"]
    if sys.argv[1:]:
        rolls = [r for r in rolls if r["druid"] in sys.argv[1:]]

    def one(roll):
        teilung = measured.get(roll["druid"], {}).get("pitch", {}).get("teilung")
        try:
            result = measure(roll, teilung or TEILUNG)
        except Exception as error:                  # noqa: BLE001
            result = {"call": "failed", "problems": [str(error)]}
        if not teilung:
            result.setdefault("problems", []).append(f"no Teilung measured; {TEILUNG} mm assumed")
        print(roll["druid"], result.get("call"), result.get("strength"), flush=True)
        return roll["druid"], result

    with ThreadPoolExecutor(WORKERS) as pool:
        results = dict(pool.map(one, rolls))
    if sys.argv[1:] and TARGET.exists():
        results = {**json.loads(TARGET.read_text()), **results}
    TARGET.write_text(json.dumps(dict(sorted(results.items())), separators=(",", ":")))
    calls = [r["call"] for r in results.values()]
    print({c: calls.count(c) for c in ("ruled", "no", "uncertain", "failed")})


if __name__ == "__main__":
    main()
