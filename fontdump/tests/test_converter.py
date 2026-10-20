#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Lee Matthew Jackson - PcW16ers.net & leematthewjackson.com
"""Tests of the Linux tools on SYNTHETIC capture files (made-up pixel
patterns, not PcW16 typefaces), so they run anywhere with Python 3,
fontTools and Pillow:

  python3 tests/test_converter.py

Includes negative tests: an incomplete file, a clipped glyph, a moved
outline point and a wrong spacing model must all be reported.
"""
import random
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))
import fdconvert as fc  # noqa: E402

failed = False


def check(cond, msg):
    global failed
    print(("PASS " if cond else "FAIL ") + msg)
    failed |= not cond


def run(*args):
    return subprocess.run([sys.executable, "-I", *map(str, args)], capture_output=True, text=True)


# ---------------------------------------------------------------------------
# a synthetic FD6 writer (docs/FORMAT.md, version 6)
# ---------------------------------------------------------------------------
UPP = 24   # synthetic 1/1800" units per pixel


def synth_rows(code, acc, size, style):
    """Made-up glyph: (rows, rows above the baseline, x offset). None = undefined."""
    if code == 0x20:
        return [], 0, 0
    if not 0x21 <= code <= 0x7E or (acc and code not in (0x41, 0x61, 0x65)):
        return None
    k = max(1, size // 12)
    w, h = 3 + code % 4, 7
    rows = ["".join("#" if (x * 7 + y * 3 + code) % 5 < 2 or y == h - 1 else "." for x in range(w)) for y in range(h)]
    if code == 0x5F:                                   # underscore: below the baseline
        rows, base = ["#" * w], -1
    else:
        base = 7
    if acc:
        rows = ["#" * w, "." * w] + rows
        base += 2
    rows = ["".join(c * k for c in r) for r in rows for _ in range(k)]
    base *= k
    if style & 1:
        rows = ["".join("#" if r[x] == "#" or (x and r[x - 1] == "#") else "." for x in range(len(r))) + r[-1]
                for r in rows]
    if style & 2:
        sh = [max(0, (base - i) // 3) for i in range(len(rows))]
        wmax = len(rows[0]) + max(sh)
        rows = ["." * s + r + "." * (wmax - s - len(r)) for s, r in zip(sh, rows)]
    return rows, base, 0


def rec(tag, body):
    return tag + struct.pack("<H", len(body)) + body


def fd6(fid, styles, style, size, name, complete=True, clip=None, pos=0, wider=0, margin=4):
    """Bytes of a synthetic FD6 file. clip = code whose glyph touches the rect edge."""
    out = b"P16FONT6" + bytes([6, 4, pos, size, fid & 255, fid >> 8, styles | 1, style])
    entry = struct.pack("<HBB", fid, styles, 0) + name.ljust(33, b"\0")
    out += rec(b"FACE", entry + bytes([0, 0, 0, 0xFF, 1, ord("C")]))
    out += rec(b"INFO", bytes([0, 0x80, 0x2E]) + struct.pack("<4H", 16 * size * 25 // 12, 9 * UPP * max(1, size // 12),
                                                               3 * UPP * max(1, size // 12), 8 * UPP))
    out += rec(b"TIM0", bytes([0, 0, 0, 0]))
    bases = [0x20] + list(range(0x41, 0x5B)) + list(range(0x61, 0x7B)) + [0x91, 0x92, 0x93, 0x94, 0x9B, 0x9D]
    for code, acc in [(c, 0) for c in range(1, 0x100)] + [(b, a) for a in range(0xD0, 0xE0) for b in bases]:
        g = synth_rows(code, acc, size, style)
        if g is None:
            out += rec(b"GLY4", struct.pack("<BBBBBHhhBBBHHHHHHB", code, acc, style, 5, 0, 0, 0, 0,
                                            0xFF, 0xFF, 0, 160, 200, 0, 0, 0, 0, 0) + b"\0")
            continue
        rows, base, xoff = g
        w = len(rows[0]) if rows else 4
        mx, my = margin, 3
        rw = ((w + 2 * mx + 7) // 8) * 8
        rh = 12 * max(1, size // 12) + 2 * my + 8
        rx, ry = 160 - mx, 200 - (9 * max(1, size // 12) + my + 2)
        if code == clip:
            rx = 160 - xoff   # glyph starts at the rect's left edge
        rowb = rw // 8
        Wb, Kb = bytearray(b"\xff" * rowb * rh), bytearray(rowb * rh)
        for y in range(rh):
            for x in range(rw):
                gx, gy = rx + x - 160 - xoff, ry + y - (200 - base)
                inbox = rows and 0 <= gy < len(rows) and 0 <= gx < w
                if inbox and rows[gy][gx] == "#":
                    Wb[y * rowb + x // 8] &= ~(0x80 >> x % 8)
                if inbox and rows[gy][gx] != "#":
                    Kb[y * rowb + x // 8] |= 0x80 >> x % 8
        if not rows:  # space: a blank box 4 px wide, 1 row
            gx0, gy0 = 160 - rx, 199 - ry
            for x in range(4):
                Kb[gy0 * rowb + (gx0 + x) // 8] |= 0x80 >> (gx0 + x) % 8
        hdr = struct.pack("<BBBBBHhhBBBHHHHHHB", code, acc, style, 0, 0, (w + 1) * UPP + wider, 10 * UPP, base * UPP,
                          0, 0, 0, 160, 200, rx, ry, rw, rh, rowb) + b"\0"
        out += rec(b"GLY4", hdr + bytes(Wb) + bytes(Kb))
    out += rec(b"TIM1", bytes([0, 2, 0, 0]))
    if complete:
        out += rec(b"END ", b"")
    return out


# 1. outline tracing: random pixel sets with holes and corner contacts
def wind(loops, x, y):
    w = 0
    for L in loops:
        for i in range(len(L)):
            (x0, y0), (x1, y1) = L[i], L[(i + 1) % len(L)]
            if x0 == x1 and x0 > x and min(y0, y1) < y < max(y0, y1):
                w += 1 if y1 > y0 else -1
    return w


random.seed(16)
bad = 0
for _ in range(2000):
    ink = {(random.randrange(9), random.randrange(9)) for _ in range(random.randrange(1, 50))}
    loops = fc.pixel_outlines(ink)
    if {(x, y) for x in range(-1, 10) for y in range(-1, 10) if wind(loops, x + .5, y + .5)} != ink:
        bad += 1
check(bad == 0, "pixel_outlines: 2000 random pixel sets traced exactly")

# 2. Unicode mapping (Rosanne codes identified from the Times/Swiss glyphs; accents composed)
G = lambda code, acc=0: {"code": code, "accent": acc}  # noqa: E731
cases = [(G(0x88), 0x2663), (G(0x8C), 0x2191), (G(0xA5), 0x2713), (G(0x60), 0x2018), (G(0x65, 0xD1), 0xE9),
         (G(0x41, 0xD5), 0xC5), (G(0x63, 0xDE), 0xE7), (G(0x69, 0xD2), 0xEF), (G(0x64, 0xDB), 0x010F),
         (G(0x74, 0xDB), 0x0165), (G(0x43, 0xD4), 0x010C), (G(0x20, 0xD1), 0x00B4), (G(0x91, 0xD1), 0x01FC),
         (G(0x42, 0xD0), 0xF042), (G(0xB5), 0xE0B5)]
wrong = [(hex(g["code"]), hex(g["accent"]), hex(fc.unicode_for(g, False)), hex(w))
         for g, w in cases if fc.unicode_for(g, False) != w]
check(not wrong, f"unicode_for: symbols, composed accents, apostrophe forms, Private Use Area {wrong}")

with tempfile.TemporaryDirectory() as t:
    t = Path(t)
    caps = t / "caps"
    caps.mkdir()
    # two faces: an ID with Normal + Italic at 12 and 24pt, a second font with Bold at 12pt only
    (caps / "F0123N12.FD6").write_bytes(fd6(0x0123, 0x05, 0, 12, b"Test Serif"))
    (caps / "F0123I12.FD6").write_bytes(fd6(0x0123, 0x05, 2, 12, b"Test Serif"))
    (caps / "F0123N24.FD6").write_bytes(fd6(0x0123, 0x05, 0, 24, b"Test Serif"))
    (caps / "F0456B12.FD6").write_bytes(fd6(0x0456, 0x03, 1, 12, b"Test Sans"))

    # 3. signed metrics: the synthetic underscore lies below the baseline
    r = fc.parse((caps / "F0123N12.FD6").read_bytes())
    u = next(g for g in r["glyphs"] if g["code"] == 0x5F and not g["accent"])
    check(r["version"] == 6 and u["charinfo"]["baseline"] < 0 and u["box"]["top"] < 0,
          f"parse: FD6 header; signed baseline {u['charinfo']['baseline']}, box top {u['box']['top']}")

    # 4. convert, then verify (must pass)
    p = run(TOOLS / "fdconvert.py", caps, "--out", t / "fonts", "--family-sizes", "24")
    check(p.returncode == 0, "fdconvert on synthetic captures\n   " + p.stdout.strip().replace("\n", "\n   ")[-600:])
    dirs = sorted(d.name for d in (t / "fonts").iterdir() if d.is_dir())
    check(dirs == ["TestSans-Bold-12pt", "TestSerif-Italic-12pt", "TestSerif-Regular-12pt", "TestSerif-Regular-24pt",
                   "family"], f"one folder per font, style and size {dirs}")
    fam = sorted(str(f.relative_to(t / "fonts")) for f in (t / "fonts" / "family").rglob("*.ttf"))
    check(fam == ["family/24pt/PcW16TestSerif-Regular.ttf", "family/PcW16TestSans-Bold.ttf",
                  "family/PcW16TestSerif-Italic.ttf", "family/PcW16TestSerif-Regular.ttf"],
          f"family fonts from 12pt, plus the 24pt set; nothing synthesised {fam}")
    check("no 12pt capture" not in p.stdout, "no missing-master note when every face has 12pt")
    from fontTools.ttLib import TTFont  # noqa: E402
    f = TTFont(str(t / "fonts" / "family" / "PcW16TestSerif-Italic.ttf"))
    check(f["name"].getDebugName(1) == "PcW16 Test Serif" and f["OS/2"].fsSelection & 1 and f["head"].macStyle == 2
          and f.getBestCmap().get(0xE9) and f.getBestCmap().get(0xF042) is None,
          "Italic family font: name, italic flags, é composed; no glyph for undefined combinations")
    v = run(TOOLS / "verify_fonts.py", caps, "--fonts", t / "fonts")
    check(v.returncode == 0 and "FAIL" not in v.stdout, "verify_fonts passes on correct fonts\n   "
          + v.stdout.strip().replace("\n", "\n   ")[-400:])
    c = run(TOOLS / "chartable.py", t / "fonts")
    check(c.returncode == 0 and (t / "fonts" / "family" / "Characters-PcW16TestSerif-Italic.md").exists(),
          "chartable writes one table per face")

    # 5. a Word Processor "screenshot" drawn at the WP spacing model must pass
    # H1, and fail with a wrong model
    from PIL import Image  # noqa: E402
    import json  # noqa: E402
    meta = json.loads((t / "fonts" / "TestSerif-Regular-24pt" / "metadata.json").read_text())
    g = {x["code"]: x for x in meta["glyphs"] if "box" in x and not x.get("accent")}
    text, x = "Hello Test", 0.0
    im = Image.new("L", (400, 80), 255)
    for ch in text:
        q = g[ord(ch)]
        for r_, row in enumerate(q["box_rows"]):
            for k, val in enumerate(row):
                if val == "#":
                    im.putpixel((10 + int(x) + q["box"]["left"] + k, 50 - q["box"]["top"] + r_), 0)
        x += q["charinfo"]["width"] / fc.WP_UNITS_PER_PX
    im.save(t / "shot.png")
    spec = ["--wp-screenshot", f"TestSerif-Regular:24:{text}:{t / 'shot.png'}"]
    v = run(TOOLS / "verify_fonts.py", caps, "--fonts", t / "fonts", *spec)
    check(v.returncode == 0 and "PASS H1" in v.stdout, "H1 passes for a screenshot at the WP spacing model")
    v = run(TOOLS / "verify_fonts.py", caps, "--fonts", t / "fonts", "--wp-units-per-px", "30", *spec)
    check(v.returncode == 1 and "FAIL H1" in v.stdout, "H1 FAILS with a wrong spacing model (30 units/px)")

    # 6. a repeat run of the same face must compare identical, even with other
    # capture margins (as FONTDMP4 vs FONTCAP); different metrics must not
    (t / "again").mkdir()
    (t / "again" / "F0123N12.FD6").write_bytes(fd6(0x0123, 0x05, 0, 12, b"Test Serif", margin=9))
    v = run(TOOLS / "verify_fonts.py", caps, "--fonts", t / "fonts", "--repeat-run", t / "again")
    check(v.returncode == 0 and "PASS H2" in v.stdout, "H2: a repeat capture with other margins compares identical")
    (t / "other").mkdir()
    (t / "other" / "F0123N12.FD6").write_bytes(fd6(0x0123, 0x05, 0, 12, b"Test Serif", wider=5))
    v = run(TOOLS / "verify_fonts.py", caps, "--fonts", t / "fonts", "--repeat-run", t / "other")
    check(v.returncode == 1 and "FAIL H2" in v.stdout, "H2 FAILS when a repeat capture has different metrics")

    # 7. negative: one contour moved by one pixel must fail C2
    fp = t / "fonts" / "TestSerif-Regular-12pt" / "PcW16-TestSerif-Regular-12.ttf"
    font = TTFont(str(fp))
    gl = font["glyf"]["R41"]
    for i in range(gl.endPtsOfContours[0] + 1):
        gl.coordinates[i] = (gl.coordinates[i][0] + 64, gl.coordinates[i][1])
    font.save(str(fp))
    v = run(TOOLS / "verify_fonts.py", caps, "--fonts", t / "fonts")
    check(v.returncode == 1 and "FAIL C2 TestSerif-Regular-12pt" in v.stdout,
          "verify_fonts FAILS C2 when one contour moves by one pixel")

    fp2 = t / "fonts" / "TestSerif-Italic-12pt" / "PcW16-TestSerif-Italic-12.ttf"
    font = TTFont(str(fp2))
    gl = font["glyf"]["R45"]
    gl.coordinates[0] = (gl.coordinates[0][0] + 64, gl.coordinates[0][1])
    font.save(str(fp2))
    v = run(TOOLS / "verify_fonts.py", caps, "--fonts", t / "fonts")
    check(v.returncode == 1 and "FAIL C2 TestSerif-Italic-12pt" in v.stdout,
          "verify_fonts FAILS C2 when a single outline point moves (a slanted edge)")

    # 8. negative: an incomplete file and a clipped glyph must be reported
    bad = t / "bad"
    bad.mkdir()
    (bad / "F0777N12.FD6").write_bytes(fd6(0x0777, 0x01, 0, 12, b"Broken", complete=False))
    (bad / "F0778N12.FD6").write_bytes(fd6(0x0778, 0x01, 0, 12, b"Clipped", clip=0x48))
    p = run(TOOLS / "fdconvert.py", bad, "--out", t / "bad-out")
    check(p.returncode == 1 and "INCOMPLETE" in p.stdout and "touches the capture edge" in p.stdout and " 48" in p.stdout,
          "fdconvert reports an incomplete file and a glyph touching its capture edge (exit 1)")

    # 9. two listed fonts with one name are kept apart by ID; a face without
    # the master size gets a note, not a family font
    two = t / "two"
    two.mkdir()
    (two / "F0801N12.FD6").write_bytes(fd6(0x0801, 0x01, 0, 12, b"Same"))
    (two / "F0802N10.FD6").write_bytes(fd6(0x0802, 0x01, 0, 10, b"Same"))
    p = run(TOOLS / "fdconvert.py", two, "--out", t / "two-out")
    dirs = sorted(d.name for d in (t / "two-out").iterdir() if d.is_dir())
    check(p.returncode == 0 and dirs == ["Same0801-Regular-12pt", "Same0802-Regular-10pt", "family"]
          and "no 12pt capture of PcW16 Same 0802" in p.stdout,
          f"same name, two IDs: separate folders; missing master size noted {dirs}")

    # 10. not a capture file
    (t / "junk.FD6").write_bytes(b"hello")
    p = run(TOOLS / "fdconvert.py", t / "junk.FD6", "--out", t / "junk-out")
    check(p.returncode != 0 and "not a capture file" in p.stderr, "fdconvert refuses a file that is not a capture")

sys.exit(1 if failed else 0)
