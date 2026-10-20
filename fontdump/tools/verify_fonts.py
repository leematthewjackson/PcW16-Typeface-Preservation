#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Lee Matthew Jackson - PcW16ers.net & leematthewjackson.com
"""Verify reconstructed PcW16 fonts against their captures and against
genuine Rosanne output.

  python3 verify_fonts.py CAPTURE_DIR [...] --fonts FONTS_DIR
          [--wp-screenshot NAME-STYLE:SIZE:TEXT:PNG ...] [--repeat-run DIR]

FONTS_DIR is fdconvert.py's output for the same captures (same options).

Two kinds of check, reported separately:

INTERNAL CONSISTENCY: the fonts faithfully hold what was captured. These
checks cannot show that the capture itself is right.
  C1  every capture file is complete (END record); no inked glyph touches its
      capture rect; no rect was clamped
  C2  every TTF glyph outline, rasterised, equals the captured pixels;
      advances equal the chosen advance; empty glyphs have no contours
  C3  every BDF glyph bitmap, BBX and DWIDTH equal the capture
  C4  cmap: every font glyph mapped exactly once
  C5  the family fonts equal the --family-master (default 12pt) captures
  C6  OpenType Sanitizer (as used by Chrome/Firefox) accepts every TTF
      (skipped if the 'opentype-sanitizer' package is missing)

HISTORICAL ACCURACY: comparison with output Rosanne itself produced.
  H1  your PcW16 Word Processor screenshots (1:1, one line of black text on
      white, e.g. Times-Regular:72:This is a test:shot.png): each letter's ink
      equals the captured glyph exactly, at a position within +-1 px of the WP
      spacing model (accumulated 1/1800" widths / units-per-px)
  H2  repeat run: glyphs and metrics of a second capture of the same
      face/size are identical (Rosanne renders deterministically)

Exit status 1 if any check fails.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fdconvert as fc  # noqa: E402

RESULTS = {"consistency": [], "historical": []}


def report(kind, ok, msg):
    RESULTS[kind].append(ok)
    print(("PASS " if ok else "FAIL ") + msg)


def winding_pixels(glyph, glyf, px):
    if glyph.numberOfContours <= 0:
        return set()
    co, ends, _ = glyph.getCoordinates(glyf)
    loops, st = [], 0
    for e in ends:
        loops.append([(x / px, y / px) for x, y in co[st:e + 1]])
        st = e + 1
    xs = [p[0] for L in loops for p in L]
    ys = [p[1] for L in loops for p in L]
    out = set()
    for X in range(int(min(xs)), int(max(xs))):
        for Y in range(int(min(ys)), int(max(ys))):
            w = 0
            for L in loops:   # non-zero winding at the pixel centre, edges at any angle
                for i in range(len(L)):
                    (x0, y0), (x1, y1) = L[i], L[(i + 1) % len(L)]
                    if min(y0, y1) < Y + .5 < max(y0, y1) and \
                            x0 + (Y + .5 - y0) * (x1 - x0) / (y1 - y0) > X + .5:
                        w += 1 if y1 > y0 else -1
            if w:
                out.add((X, Y))
    return out


def ink_set(g):
    b = g["box"]
    return {(b["left"] + k, b["top"] - r - 1) for r, row in enumerate(g["box_rows"])
            for k, v in enumerate(row) if v == "#"}


def parse_bdf(path):
    chars, cur, bm = {}, None, None
    for line in path.read_text().splitlines():
        t = line.split()
        if not t:
            continue
        if t[0] == "STARTCHAR":
            cur = {"name": t[1]}
        elif t[0] in ("ENCODING", "DWIDTH") and cur is not None:
            cur[t[0]] = int(t[1])
        elif t[0] == "BBX" and cur is not None:
            cur["BBX"] = tuple(map(int, t[1:5]))
        elif t[0] == "BITMAP":
            bm = []
        elif t[0] == "ENDCHAR":
            cur["bitmap"] = bm
            chars[cur["name"]] = cur
            cur, bm = None, None
        elif bm is not None:
            bm.append(line.strip())
    return chars


def bdf_pixels(c):
    w, h, xo, yo = c["BBX"]
    out = set()
    for r, hexrow in enumerate(c["bitmap"]):
        bits = bin(int(hexrow, 16))[2:].zfill(len(hexrow) * 4)
        for k in range(w):
            if bits[k] == "1":
                out.add((xo + k, yo + h - 1 - r))
    return out


def check_group(paths, fonts, master):
    from fontTools.ttLib import TTFont
    rep = fc.merge(paths)
    fi = fc.face_info(rep)
    tag = f"{fi['tag']}-{rep['size']:02d}pt"
    gl = [g for g in rep["glyphs"] if "box" in g]
    clipped = [fc.label(g) for g in gl if g["touches_rect_edge"] and g["ink_pixels"]]
    clamped = [fc.label(g) for g in rep["glyphs"] if g["flags"]]
    report("consistency", rep["complete"] and not clipped and not clamped,
           f"C1 {tag}: complete={rep['complete']} clipped={clipped[:5]} clamped={clamped[:5]}")
    font_gl = fc.font_glyphs(rep)
    d = fonts / tag
    ttf = TTFont(str(d / f"{fi['stem']}-{rep['size']}.ttf"))
    glyf, cmap, hmtx = ttf["glyf"], ttf.getBestCmap(), ttf["hmtx"]
    px = 64
    bad_o, bad_a, bad_c = [], [], []
    for g in font_gl:
        name = "R" + fc.label(g).replace("+", "_")
        u = fc.unicode_for(g, False)
        if cmap.get(u) != name:
            bad_c.append(fc.label(g))
            continue
        if winding_pixels(glyf[name], glyf, px) != ink_set(g):
            bad_o.append(fc.label(g))
        if hmtx[name][0] != round(fc.advance(g) * px):
            bad_a.append(fc.label(g))
    report("consistency", not bad_o and not bad_a,
           f"C2 {tag}: {len(font_gl)} TTF outlines == captured pixels, advances as chosen "
           f"(outline errors {bad_o[:5]}, advance errors {bad_a[:5]})")
    names = {"R" + fc.label(g).replace("+", "_") for g in font_gl}
    report("consistency", not bad_c and len(cmap) == len(font_gl) and set(cmap.values()) == names,
           f"C4 {tag}: cmap maps {len(cmap)} code points to {len(font_gl)} glyphs exactly once {bad_c[:5]}")
    bdf = parse_bdf(d / f"{fi['stem']}-{rep['size']}.bdf")
    bad_b = []
    for g in font_gl:
        c = bdf.get("R" + fc.label(g).replace("+", "_"))
        b = g["box"]
        if (c is None or bdf_pixels(c) != ink_set(g) or c["DWIDTH"] != round(fc.advance(g))
                or c["BBX"][:3] != (b["width"], b["height"], b["left"])):
            bad_b.append(fc.label(g))
    report("consistency", not bad_b and len(bdf) == len(font_gl),
           f"C3 {tag}: {len(bdf)} BDF bitmaps, BBX and DWIDTH == capture {bad_b[:5]}")
    if rep["size"] == master:
        fttf = TTFont(str(fonts / "family" / f"{fi['family_file']}.ttf"))
        same = all(fttf["glyf"][n].getCoordinates(fttf["glyf"])[0] == glyf[n].getCoordinates(glyf)[0]
                   and fttf["hmtx"][n] == hmtx[n] for n in names)
        report("consistency", same, f"C5 family {fi['family']} {fi['style']} == {tag} outlines and advances")
    return rep


def check_screenshot(spec, fonts):
    from PIL import Image
    face, size, text, png = spec.split(":", 3)
    meta = json.loads((fonts / f"{face}-{int(size):02d}pt" / "metadata.json").read_text())   # face = Name-Style
    g = {x["code"]: x for x in meta["glyphs"] if "box" in x and not x.get("accent")}
    im = Image.open(png).convert("L")
    P, W, H = im.load(), im.width, im.height
    shot = {(x, y) for y in range(H) for x in range(W) if P[x, y] < 128}
    # model positions (y down, relative to the first letter's ink)
    x, letters = 0.0, []
    for ch in text:
        q = g[ord(ch)]
        if q["ink_pixels"]:
            ink = {(int(x) + q["box"]["left"] + k, -q["box"]["top"] + r) for r, row in enumerate(q["box_rows"])
                   for k, v in enumerate(row) if v == "#"}
            letters.append((ch, ink))
        x += q["charinfo"]["width"] / fc.ADVANCE["upp"]
    first = letters[0][1]
    sx, sy = min(p[0] for p in shot), min(p[1] for p in shot)
    fx, fy = min(p[0] for p in first), min(p[1] for p in first)
    ox, oy = sx - fx, sy - fy
    exact, offs, used = 0, [], set()
    for ch, ink in letters:
        best = None
        for dx in (-1, 0, 1):
            moved = {(a + ox + dx, b + oy) for a, b in ink}
            if moved <= shot:
                best = dx
                used |= moved
                break
        if best is not None:
            exact += 1
            offs.append(best)
    leftover = len(shot - used)
    report("historical", exact == len(letters) and leftover == 0,
           f"H1 {face} {size}pt WP screenshot {Path(png).name}: {exact}/{len(letters)} letters' ink identical to "
           f"the capture at WP spacing {fc.ADVANCE['upp']} units/px +- 1 px (offsets {offs}); "
           f"screenshot ink not accounted for: {leftover} px")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("captures", nargs="+", type=Path)
    ap.add_argument("--fonts", type=Path, required=True)
    ap.add_argument("--family-master", type=int, default=12)
    ap.add_argument("--wp-screenshot", action="append", default=[])
    ap.add_argument("--repeat-run", type=Path)
    ap.add_argument("--wp-units-per-px", type=float, default=fc.WP_UNITS_PER_PX)
    ap.add_argument("--family-prefix", default="PcW16")
    a = ap.parse_args()
    fc.ADVANCE.update(mode="wp", upp=a.wp_units_per_px)
    fc.FAMILY_PREFIX["prefix"] = a.family_prefix
    files = [q for p in a.captures for q in (sorted(p.iterdir()) if p.is_dir() else [p])
             if q.suffix.upper() in (".FD4", ".FD5", ".FD6")]
    groups = {}
    for f in files:
        r = fc.parse(f.read_bytes())
        groups.setdefault((r["font_id"], r["style"] & 3, r["size"]), []).append(f)
    print("== internal consistency ==")
    reps = {k: check_group(v, a.fonts, a.family_master) for k, v in sorted(groups.items())}
    try:
        import ots
        ttfs = sorted(a.fonts.glob("**/*.ttf"))
        bad = [t.name for t in ttfs if ots.sanitize(str(t), "/dev/null", capture_output=True).returncode]
        report("consistency", not bad, f"C6 OpenType Sanitizer accepts {len(ttfs) - len(bad)}/{len(ttfs)} TTFs {bad[:5]}")
    except ImportError:
        print("SKIP C6 (pip install opentype-sanitizer)")
    print("== historical accuracy ==")
    for spec in a.wp_screenshot:
        check_screenshot(spec, a.fonts)
    if a.repeat_run:
        for f in sorted(a.repeat_run.iterdir()):
            if f.suffix.upper() not in (".FD4", ".FD5", ".FD6"):
                continue
            r2 = fc.parse(f.read_bytes())
            r1 = reps.get((r2["font_id"], r2["style"] & 3, r2["size"]))
            if r1:
                # compare the glyph itself, not where it sat in its capture rect
                # (FONTCAP's margins differ from FONTDMP4's)
                def key(g):
                    b = {k: v for k, v in (g.get("box") or {}).items() if k != "rect_xy"}
                    return g.get("box_rows"), b, g["charinfo"]
                def blank_unsure(a, b):
                    # no ink in either, same metrics, but the (empty) raster box is
                    # missing or at the rect edge in one of them: a box the capture
                    # rect did not fully hold (e.g. the blank B0-CF placeholders,
                    # whose metrics lie outside the font's ascender at small sizes)
                    return (not a.get("ink_pixels") and not b.get("ink_pixels") and a["charinfo"] == b["charinfo"]
                            and any("box" not in q or q.get("touches_rect_edge") for q in (a, b)))
                first = {(g["code"], g["accent"]): g for g in r1["glyphs"]}
                same, unsure = True, 0
                for x in r2["glyphs"]:
                    y = first.get((x["code"], x["accent"]))
                    if y is None:
                        same = False
                    elif key(y) != key(x):
                        if blank_unsure(x, y):
                            unsure += 1
                        else:
                            same = False
                report("historical", same, f"H2 repeat run {f.name}: glyphs and metrics identical"
                       + (f" ({unsure} blank glyphs with an edge-clipped empty box: metrics identical)" if unsure else ""))
    for k, v in RESULTS.items():
        print(f"{k}: {sum(v)}/{len(v)} passed")
    return 0 if all(all(v) for v in RESULTS.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
