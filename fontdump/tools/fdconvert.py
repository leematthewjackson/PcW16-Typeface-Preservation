#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Lee Matthew Jackson - PcW16ers.net & leematthewjackson.com
"""Convert PcW16 typeface captures (FONTCAP .FD6 files; FONTDMP4/5 .FD4/.FD5
files) into bitmap and TrueType fonts, PNG sheets and metadata.

  python3 fdconvert.py CAPTURE_DIR [MORE_DIRS_OR_FILES ...] --out DIR

Files are grouped by font ID, style and size (from their headers), so the
captures can sit in any folders you list. For each group, in DIR under
<Name>-<Style>-<size>pt/:
  PcW16-<Name>-<Style>-<size>.bdf  BDF bitmap font: the pixels exactly as Rosanne
                                drew them; advances as the PcW16 Word Processor
                                spaces text (--advance box: the raster box)
  PcW16-<Name>-<Style>-<size>.ttf  "pixel TTF": one square per pixel, traced into
                                seam-free outlines, same metrics (needs fontTools)
  sheet.png, sheet-accents.png  every glyph, enlarged, labelled with its code
  glyphs/<code>.png             each glyph's box, 1:1
  metadata.json                 per glyph: Rosanne metrics (1/1800 inch), box,
                                ink, advance, flags; font info; capture timing
and in DIR/family/: PcW16<Name>-<Style>.ttf, one installable font per face
("PcW16 <Name>", its listed styles) built from the --family-master size
(default 12pt); --family-sizes 10,14 adds the same set from other sizes in
family/<NN>pt/. No style is synthesised: only the styles Rosanne reported.
Exit status 1 if any file is incomplete or any glyph may be clipped.

Encoding: Rosanne's character set is not Latin-1. ROSANNE_TO_UNICODE maps
codes 20-AF to Unicode, identified from the glyphs Rosanne drew for Times
and Swiss (docs/AUDIT.md). B0-CF are blank user-definable slots in those
fonts: left out of the fonts when blank. Codes and accent combinations with
no Unicode equivalent go to the Private Use Area (U+E000 + code, U+F000 +
(accent - D0) * 256 + code). --raw-encoding writes the Rosanne codes instead.
"""
import argparse
import unicodedata
import json
import struct
import sys
from pathlib import Path

STYLE_NAMES = {0: "Regular", 1: "Bold", 2: "Italic", 3: "Bold Italic"}  # charscreen style bit 0 Bold, bit 1 Italic
LEGACY_NAMES = {0: "Times", 1: "Times", 2: "Swiss"}   # FONTDMP4/5 face index, if a file has no FACE record
FAMILY_PREFIX = {"prefix": "PcW16"}
NAME_OVERRIDE = {}   # font ID -> name, when two listed fonts share a name
GH_LEN = 28

# Rosanne -> Unicode, identified from the glyphs Rosanne itself drew (XAnne
# runs 4-6, Times and Swiss, docs/AUDIT.md). ROSAN283's printed table
# is garbled or out of date for 80-8F (the release fonts have card suits and
# arrows there). B0-CF are blank placeholders in the release fonts.
ROSANNE_TO_UNICODE = {c: c for c in range(0x20, 0x7F)}
ROSANNE_TO_UNICODE.update({
    0x60: 0x2018, 0x7F: 0x2019,                                  # open / close single quote
    0x80: 0x201C, 0x81: 0x201D, 0x82: 0x201E,                    # double quotes, German open quote
    0x83: 0x2022, 0x84: 0x25CF, 0x85: 0x25CB,                    # small bullet, black circle, white circle
    0x86: 0x00A5, 0x87: 0x00A4,                                  # yen, currency sign
    0x88: 0x2663, 0x89: 0x2666, 0x8A: 0x2665, 0x8B: 0x2660,      # club, diamond, heart, spade
    0x8C: 0x2191, 0x8D: 0x2193, 0x8E: 0x2190, 0x8F: 0x2192,      # arrows up, down, left, right
    0x90: 0x00DF, 0x91: 0x00C6, 0x92: 0x00E6, 0x93: 0x0152, 0x94: 0x0153,
    0x95: 0x2105, 0x96: 0x2122, 0x97: 0x00A9,                    # care of, trade mark, copyright
    0x98: 0x266D, 0x99: 0x266E,                                  # musical flat, natural
    0x9A: 0x00A2, 0x9B: 0x00F8, 0x9C: 0x00A3, 0x9D: 0x00D8, 0x9E: 0x00D7, 0x9F: 0x00B1,
    0xA0: 0x2212, 0xA1: 0x00F7, 0xA2: 0x00B7, 0xA3: 0x00B0,      # minus, divide, middle dot, degree
    0xA4: 0x2717, 0xA5: 0x2713,                                  # ballot X, check mark
    0xA6: 0x2020, 0xA7: 0x2021, 0xA8: 0x00BF, 0xA9: 0x00AE,
    0xAA: 0x00BE, 0xAB: 0x00BD, 0xAC: 0x00BC, 0xAD: 0x00A1, 0xAE: 0x00AB, 0xAF: 0x00BB,
})
BLANK_RANGE = range(0xB0, 0xD0)   # user-definable slots, blank: left out of the fonts

# Advance widths. "wp" (default): as the PcW16 Word Processor spaces text --
# the 1/1800" charinfo width accumulated at WP_UNITS_PER_PX. Measured from the
# 72pt Times and Swiss Word Processor screenshots (XAnne run 5). With the strict
# check (tools/verify_fonts.py H1: every letter's ink identical to the capture,
# within +-1 px of the model, no screenshot ink left over) both lines pass for
# 24.15-24.20 units/px and fail at 24.14 and 24.21; the default is the centre
# of that interval (audit, docs/AUDIT.md). One line per face at one size:
# more screenshots (12pt, long lines) would narrow it further.
# "box": the width of the raster box os_typo_charscreen paints.
WP_UNITS_PER_PX = 24.175
ADVANCE = {"mode": "wp", "upp": WP_UNITS_PER_PX}


def advance(g):
    """Advance in pixels (float for "wp")."""
    if ADVANCE["mode"] == "box":
        return float(g["advance_px"])
    return g["charinfo"]["width"] / ADVANCE["upp"]


def bits_to_rows(data, w, h):
    rowb = (w + 7) // 8
    return [[(data[y * rowb + x // 8] >> (7 - x % 8)) & 1 for x in range(w)] for y in range(h)]


def parse(blob):
    if blob[:8] not in (b"P16FONT4", b"P16FONT5", b"P16FONT6"):
        raise ValueError("not a capture file (magic P16FONT4/5/6)")
    ver, stage, face, size, fid_lo, fid_hi, styles, style = blob[8:16]
    rep = {"version": ver, "face": face, "size": size, "font_id": fid_lo | fid_hi << 8, "styles_defined": styles,
           "style": style, "glyphs": [], "complete": False}
    pos = 16
    while pos + 6 <= len(blob):
        tag = blob[pos:pos + 4].decode("latin-1")
        (n,) = struct.unpack_from("<H", blob, pos + 4)
        body = blob[pos + 6:pos + 6 + n]
        if len(body) < n:
            rep["truncated"] = tag
            break
        pos += 6 + n
        if tag == "FACE":
            rep["list_entry"] = {"id": struct.unpack_from("<H", body)[0], "styles": body[2], "rtf_family": body[3],
                                 "name": body[4:37].split(b"\0")[0].decode("latin-1")}
            rep.update(def_a=body[37], init_called=body[39], init_f=body[40], slot=body[41],
                       list_source=chr(body[42]) if body[42] else None)
        elif tag == "INFO":
            rep["info"] = {"a": body[0]}
            if body[0] == 0:
                rep["info"].update(zip(("line_pitch", "max_ascender", "max_descender", "widest"),
                                       struct.unpack_from("<4H", body, 3)))
        elif tag in ("TIM0", "TIM1"):
            e, d, c, b = body[:4]
            rep[tag] = b * 3600 + c * 60 + d   # whole seconds: the tick byte is not a 1/256 s up-counter
            rep[tag + "_raw"] = [e, d, c, b]   # (XAnne run 5: 209 -> 185 within one second)
        elif tag == "GLY4":
            rep["glyphs"].append(parse_glyph(body))
        elif tag == "END ":
            rep["complete"] = True
    if "TIM0" in rep and "TIM1" in rep:
        rep["dump_seconds"] = (rep["TIM1"] - rep["TIM0"]) % 86400   # +-1 s, emulated clock
    return rep


def parse_glyph(body):
    (ch, acc, sty, ci_a, ci_f, w, h, b, w_a, k_a, flags, gx, gy, rx, ry, rw, rh, rowb) = struct.unpack_from(
        "<BBBBBHhhBBBHHHHHHB", body)  # charinfo HL, BC are signed: "_" has a negative baseline
    g = {"code": ch, "accent": acc, "style": sty, "charinfo": {"a": ci_a, "width": w, "height": h, "baseline": b},
         "draw": {"W_a": w_a, "K_a": k_a}, "flags": flags, "origin": [gx, gy], "rect": [rx, ry, rw, rh]}
    if ci_a == 0 and rw and rh:
        n = rowb * rh
        g["W"] = bits_to_rows(body[GH_LEN:GH_LEN + n], rw, rh)
        g["K"] = bits_to_rows(body[GH_LEN + n:GH_LEN + 2 * n], rw, rh)
        g.update(analyse(g))
    return g


def analyse(g):
    rx, ry, rw, rh = g["rect"]
    ox, oy = g["origin"][0] - rx, g["origin"][1] - ry
    ink = {(x, y) for y in range(rh) for x in range(rw) if g["W"][y][x] == 0}
    white = {(x, y) for y in range(rh) for x in range(rw) if g["K"][y][x] == 1}
    area = ink | white
    out = {"ink_pixels": len(ink), "origin_in_rect": [ox, oy]}
    if not area:
        out["empty"] = True
        return out
    xs, ys = [p[0] for p in area], [p[1] for p in area]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    out["box"] = {"left": x0 - ox, "width": x1 - x0 + 1, "top": oy - y0, "height": y1 - y0 + 1,
                  "rect_xy": [x0, y0]}
    out["advance_px"] = x1 - x0 + 1
    out["box_solid"] = len(area) == (x1 - x0 + 1) * (y1 - y0 + 1)
    out["touches_rect_edge"] = x0 == 0 or y0 == 0 or x1 == rw - 1 or y1 == rh - 1
    out["box_rows"] = ["".join("#" if (x, y) in ink else "." for x in range(x0, x1 + 1)) for y in range(y0, y1 + 1)]
    return out


# Rosanne accents D0-DF (ROSAN283 Appendix "Accents", order as its table):
# combining marks for composing accented letters, and spacing forms for an
# accent on a space. Checked against the Times and Swiss captures (XAnne run 6).
ACCENTS = {  # code: (name, combining mark, spacing form)
    0xD0: ("grave", 0x0300, 0x0060), 0xD1: ("acute", 0x0301, 0x00B4),
    0xD2: ("umlaut", 0x0308, 0x00A8), 0xD3: ("tilde", 0x0303, 0x02DC),
    0xD4: ("hacek", 0x030C, 0x02C7), 0xD5: ("ring", 0x030A, 0x02DA),
    0xD6: ("circumflex", 0x0302, 0x02C6), 0xD7: ("dot above", 0x0307, 0x02D9),
    0xD8: ("macron", 0x0304, 0x00AF), 0xD9: ("breve", 0x0306, 0x02D8),
    0xDA: ("double acute", 0x030B, 0x02DD), 0xDB: ("apostrophe", None, 0x02BC),
    0xDC: ("dot below", 0x0323, None), 0xDD: ("comma below", 0x0326, None),
    0xDE: ("cedilla", 0x0327, 0x00B8), 0xDF: ("ogonek", 0x0328, 0x02DB),
}
APOSTROPHE_LETTERS = {ord("d"): 0x010F, ord("l"): 0x013E, ord("t"): 0x0165, ord("L"): 0x013D}


def face_info(rep):
    """Name, style and file/folder names of a capture, from its FACE record
    (the os_typo_getlist entry) and the style it was drawn in."""
    style = STYLE_NAMES.get(rep["style"] & 3, f"Style{rep['style']}")
    name = NAME_OVERRIDE.get(rep["font_id"]) or (rep.get("list_entry") or {}).get("name") \
        or (LEGACY_NAMES.get(rep["face"]) if rep["version"] < 6 else None) or f"Font{rep['font_id']:04X}"
    name = " ".join("".join(c if c.isalnum() or c in " -" else " " for c in name).split()) or f"Font{rep['font_id']:04X}"
    safe, ssafe = name.replace(" ", ""), style.replace(" ", "")
    return {"name": name, "style": style, "family": f"{FAMILY_PREFIX['prefix']} {name}",
            "tag": f"{safe}-{ssafe}", "stem": f"{FAMILY_PREFIX['prefix']}-{safe}-{ssafe}",
            "family_file": f"{FAMILY_PREFIX['prefix']}{safe}-{ssafe}",
            "bold": bool(rep["style"] & 1), "italic": bool(rep["style"] & 2)}


def label(g):
    return f"{g['code']:02X}" + (f"+{g['accent']:02X}" if g.get("accent") else "")


def unicode_for(g, raw):
    """Code point for glyph g (dict with code, accent), or a Private Use
    value: E000+code for unidentified single codes, F000+(accent-D0)*256+code
    for accent combinations with no single Unicode character."""
    code, acc = g["code"], g.get("accent", 0)
    pua = 0xF000 + (acc - 0xD0) * 256 + code if acc else 0xE000 + code
    if raw:
        return pua if acc else code
    if not acc:
        return ROSANNE_TO_UNICODE.get(code, pua)
    name, comb, spacing = ACCENTS.get(acc, (None, None, None))
    base = ROSANNE_TO_UNICODE.get(code)
    if base is None:
        return pua
    if code == 0x20:
        return spacing or pua
    if acc == 0xDB:
        return APOSTROPHE_LETTERS.get(code, pua)
    if acc == 0xD4 and code in APOSTROPHE_LETTERS:
        # d, l, t, L: Czech/Slovak typography draws this caron as an apostrophe,
        # and Rosanne has a dedicated apostrophe accent (DB) for it -- that
        # form represents U+010F/013E/0165/013D; the hacek form goes to PUA
        return pua
    composed = unicodedata.normalize("NFC", chr(base) + chr(comb)) if comb else ""
    return ord(composed) if len(composed) == 1 else pua


def font_glyphs(rep):
    """Glyphs that go into a font: drawn, not a blank B0-CF slot, and, when
    two glyphs claim one code point, the first (plain codes before accents)."""
    out, seen = [], set()
    for g in rep["glyphs"]:
        if "box" not in g or (g["code"] in BLANK_RANGE and not g.get("accent") and g["ink_pixels"] == 0):
            continue
        u = unicode_for(g, False)
        if u in seen:
            continue
        seen.add(u)
        out.append(g)
    return out


def write_bdf(rep, path, raw):
    fi = face_info(rep)
    fam, sty = fi["name"], fi["style"]
    size = rep["size"]
    gl = font_glyphs(rep)
    asc = max(g["box"]["top"] for g in gl)
    desc = max(g["box"]["height"] - g["box"]["top"] for g in gl)
    maxw = max(g["box"]["width"] for g in gl)
    minx = min(g["box"]["left"] for g in gl)
    weight = "Bold" if fi["bold"] else "Medium"
    lines = ["STARTFONT 2.1",
             f"COMMENT {fam} {sty} {size}pt screen font of an Amstrad PcW16 (Rosanne), reconstructed from",
             "COMMENT the pixels Rosanne drew (os_typo_charscreen + bios_getpxl). Pixels unaltered.",
             f"COMMENT Rosanne font ID {rep['font_id']:04X}; encoding {'Rosanne codes' if raw else 'Unicode (see metadata.json)'}",
             f"COMMENT advances: {ADVANCE['mode']}" + (f" (1/1800 in width / {ADVANCE['upp']}, rounded: PcW16 WP spacing)"
                                                       if ADVANCE['mode'] == 'wp' else " (raster box width)"),
             f"FONT -{FAMILY_PREFIX['prefix']}-{fam.replace(' ', '')}-{weight}-{'I' if fi['italic'] else 'R'}-Normal--"
             f"{asc + desc}-{size * 10}-72-72-P-{maxw * 10}-"
             + ("PcW16-Rosanne" if raw else "ISO10646-1"),
             f"SIZE {size} 72 72",
             f"FONTBOUNDINGBOX {maxw} {asc + desc} {minx} {-desc}",
             "STARTPROPERTIES 4", f"FONT_ASCENT {asc}", f"FONT_DESCENT {desc}",
             f"FAMILY_NAME \"{fi['family']}\"", f"WEIGHT_NAME \"{weight}\"", "ENDPROPERTIES",
             f"CHARS {len(gl)}"]
    em_units = size * 25  # 1/1800 inch per em at size pt
    for g in sorted(gl, key=lambda g: unicode_for(g, raw)):
        b = g["box"]
        u = unicode_for(g, raw)
        bottom = b["top"] - b["height"]
        lines += [f"STARTCHAR R{label(g).replace('+', '_')}", f"ENCODING {u}",
                  f"SWIDTH {round(g['charinfo']['width'] * 1000 / em_units)} 0",
                  f"DWIDTH {round(advance(g))} 0", f"BBX {b['width']} {b['height']} {b['left']} {bottom}", "BITMAP"]
        for row in g["box_rows"]:
            bits = row.replace("#", "1").replace(".", "0")
            bits += "0" * (-len(bits) % 8)
            lines.append("".join(f"{int(bits[i:i + 8], 2):02X}" for i in range(0, len(bits), 8)))
        lines.append("ENDCHAR")
    lines.append("ENDFONT")
    path.write_text("\n".join(lines) + "\n")


def pixel_outlines(ink):
    """Trace the union of unit pixel squares into closed outlines, so the TTF
    has no internal seams (separate abutting squares show hairline gaps in
    anti-aliasing renderers). ink: set of (x, y), pixel = [x, x+1] x [y, y+1],
    y up. Returns loops of corner points: outer boundaries clockwise, holes
    counter-clockwise (TrueType), collinear points removed. Where two pixels
    touch only at a corner, the trace turns right, keeping them separate."""
    edges = {}
    for x, y in ink:  # each square clockwise; shared edges cancel
        for a, b in (((x, y), (x, y + 1)), ((x, y + 1), (x + 1, y + 1)),
                     ((x + 1, y + 1), (x + 1, y)), ((x + 1, y), (x, y))):
            if (b, a) in edges:
                del edges[(b, a)]
            else:
                edges[(a, b)] = True
    out = {}
    for a, b in edges:
        out.setdefault(a, []).append(b)
    loops = []
    while out:
        start = next(iter(out))
        loop, prev, cur = [start], None, start
        while True:
            nxt = out[cur]
            if len(nxt) == 1 or prev is None:
                b = nxt[0]
            else:  # corner contact: prefer the right turn
                dx, dy = cur[0] - prev[0], cur[1] - prev[1]
                right = (cur[0] + dy, cur[1] - dx)
                b = right if right in nxt else nxt[0]
            nxt.remove(b)
            if not nxt:
                del out[cur]
            prev, cur = cur, b
            if cur == start and (start not in out):
                break
            if cur == start:
                break
            loop.append(cur)
        pts = [p for i, p in enumerate(loop)  # drop collinear corners
               if (loop[i - 1][0] - p[0]) * (loop[(i + 1) % len(loop)][1] - p[1])
               != (loop[i - 1][1] - p[1]) * (loop[(i + 1) % len(loop)][0] - p[0])]
        loops.append(pts)
    return loops


def write_ttf(rep, path, raw, family=None):
    try:
        from fontTools.fontBuilder import FontBuilder
        from fontTools.pens.ttGlyphPen import TTGlyphPen
    except ImportError:
        return "fontTools not installed (pip install fonttools): no TTF"
    fi = face_info(rep)
    fam, sty = fi["name"], fi["style"]
    px = 64                                  # font units per pixel
    gl = font_glyphs(rep)
    upm = rep["size"] * px                   # 1 em = size pixels at 72 dpi: render at size px for 1:1
    asc = max(g["box"]["top"] for g in gl) * px
    desc = max(g["box"]["height"] - g["box"]["top"] for g in gl) * px
    names, cmap, glyphs, metrics = [".notdef"], {}, {}, {}
    pen = TTGlyphPen(None)
    glyphs[".notdef"], metrics[".notdef"] = pen.glyph(), (upm // 2, 0)
    for g in gl:
        name = "R" + label(g).replace("+", "_")
        names.append(name)
        cmap[unicode_for(g, raw)] = name
        pen = TTGlyphPen(None)
        b = g["box"]
        ink = {(b["left"] + k, b["top"] - r - 1) for r, row in enumerate(g["box_rows"])
               for k, v in enumerate(row) if v == "#"}
        for loop in pixel_outlines(ink):
            pen.moveTo((loop[0][0] * px, loop[0][1] * px))
            for x, y in loop[1:]:
                pen.lineTo((x * px, y * px))
            pen.closePath()
        glyph = pen.glyph()
        glyphs[name] = glyph
        metrics[name] = (round(advance(g) * px), 0)     # fractional pixels kept (1/64 px)
    fb = FontBuilder(upm, isTTF=True)
    fb.setupGlyphOrder(names)
    fb.setupCharacterMap(cmap)
    fb.setupGlyf(glyphs)
    for name in names:
        glyph = glyphs[name]
        glyph.recalcBounds(fb.font["glyf"])
        metrics[name] = (metrics[name][0], getattr(glyph, "xMin", 0) if glyph.numberOfContours else 0)
    fb.setupHorizontalMetrics(metrics)
    # line spacing: Rosanne's own line pitch (os_typo_info) at the WP scale,
    # as the gap beyond the glyph extents (not yet compared with WP output)
    pitch = (rep.get("info") or {}).get("line_pitch")
    line_gap = max(0, round(pitch / ADVANCE["upp"] * px) - (asc + desc)) if pitch else 0
    fb.setupHorizontalHeader(ascent=asc, descent=-desc, lineGap=line_gap)
    famname = family or f"{fi['family']} {rep['size']}"
    full = famname + ("" if sty == "Regular" else f" {sty}")
    fb.setupNameTable({"familyName": famname, "styleName": sty,
                       "uniqueFontIdentifier": full.replace(" ", ""), "fullName": full,
                       "psName": full.replace(" ", "-"),
                       "version": f"Version 1.0 (Rosanne screen capture, {rep['size']}pt)",
                       "description": f"{fam} {sty} {rep['size']}pt screen font of an Amstrad PcW16 (Rosanne), "
                                      "reconstructed from the pixels Rosanne drew on screen, with PcW16 Typeface "
                                      "Preservation. A pixel reconstruction, not an original outline font file."})
    sel = (0x20 if fi["bold"] else 0) | (0x01 if fi["italic"] else 0)
    fb.setupOS2(version=4, sTypoAscender=asc, sTypoDescender=-desc, sTypoLineGap=line_gap, usWinAscent=asc, usWinDescent=desc,
                usWeightClass=700 if fi["bold"] else 400,
                fsSelection=(sel or 0x40) | 0x80)    # 0x40 Regular, 0x80 USE_TYPO_METRICS
    os2 = fb.font["OS/2"]
    os2.recalcUnicodeRanges(fb.font)
    os2.recalcCodePageRanges(fb.font)
    under = next((g for g in gl if g["code"] == 0x5F and not g.get("accent") and g["ink_pixels"]), None)
    if under:  # underline position and thickness from Rosanne's own underscore
        rows = under["box_rows"]
        ink_rows = [i for i, r in enumerate(rows) if "#" in r]
        fb.setupPost(underlinePosition=(under["box"]["top"] - ink_rows[0]) * px,
                     underlineThickness=len(ink_rows) * px)
    else:
        fb.setupPost()
    fb.updateHead(macStyle=(1 if fi["bold"] else 0) | (2 if fi["italic"] else 0))
    from fontTools.ttLib import newTable
    gasp = newTable("gasp")                  # pixel font: ask renderers not to grid-fit or smooth
    gasp.version, gasp.gaspRange = 1, {0xFFFF: 0}
    fb.font["gasp"] = gasp
    fb.save(str(path))
    return None


def write_pngs(rep, outdir):
    try:
        from PIL import Image, ImageDraw  # noqa: F401
    except ImportError:
        return "Pillow not installed: no PNG output"
    gdir = outdir / "glyphs"
    gdir.mkdir(exist_ok=True)
    gl = [g for g in rep["glyphs"] if "box" in g]
    for g in gl:
        rows = g["box_rows"]
        im = Image.new("1", (len(rows[0]), len(rows)), 1)
        im.putdata([0 if c == "#" else 1 for r in rows for c in r])
        im.save(gdir / f"{label(g)}.png")
    plain = [g for g in gl if not g.get("accent")]
    accented = [g for g in gl if g.get("accent")]
    if plain:
        write_sheet(plain, outdir / "sheet.png")
    if accented:
        write_sheet(accented, outdir / "sheet-accents.png", max_scale=3)
    return None


def write_sheet(gl, path, max_scale=8):
    from PIL import Image, ImageDraw
    asc = max(g["box"]["top"] for g in gl)
    desc = max(g["box"]["height"] - g["box"]["top"] for g in gl)
    cw = max(g["box"]["width"] for g in gl) + 2
    ch = asc + desc + 2
    scale = max(2, min(max_scale, 64 // ch))
    cols = 16
    tile_w, tile_h = max(cw * scale, 40) + 8, ch * scale + 22
    nrows = (len(gl) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tile_w + 8, nrows * tile_h + 8), "white")
    d = ImageDraw.Draw(sheet)
    for i, g in enumerate(gl):
        tx, ty = 8 + (i % cols) * tile_w, 8 + (i // cols) * tile_h
        b = g["box"]
        base_y = ty + (asc + 1) * scale
        d.rectangle([tx, ty, tx + cw * scale - 1, ty + ch * scale - 1], fill=(232, 238, 248))
        ox = tx + scale * (1 + b["left"] - min(0, min(x["box"]["left"] for x in gl)))
        for r, row in enumerate(g["box_rows"]):
            for c, v in enumerate(row):
                y = base_y - (b["top"] - r) * scale
                x = ox + c * scale
                d.rectangle([x, y, x + scale - 1, y + scale - 1], fill=(0, 0, 0) if v == "#" else (255, 255, 255))
        d.line([(tx, base_y), (tx + cw * scale - 1, base_y)], fill=(230, 60, 60))
        flag = "!" if b and g.get("touches_rect_edge") else ""
        d.text((tx, ty + ch * scale + 4), f"{label(g)}{flag}", fill=(0, 0, 0))
    sheet.save(path)


def merge(paths):
    """Parse the capture files of one font, style and size into one report:
    FD4 glyphs (plain codes 20-CF) first, then FD5 (01-1F, D0-FF, accents),
    then FD6 (everything). A code captured twice keeps the first capture."""
    reps = sorted((parse(p.read_bytes()) for p in paths), key=lambda r: r["version"])
    rep = dict(reps[0])
    seen, rep["glyphs"] = set(), []
    for g in (g for r in reps for g in r["glyphs"]):
        if (g["code"], g["accent"]) not in seen:
            seen.add((g["code"], g["accent"]))
            rep["glyphs"].append(g)
    rep["complete"] = all(r["complete"] for r in reps)
    rep["sources"] = [p.name for p in sorted(paths)]
    rep["dump_seconds"] = sum(r.get("dump_seconds") or 0 for r in reps)
    return rep


def convert(paths, outroot, raw):
    rep = merge(paths)
    path = Path(" + ".join(rep["sources"]))
    fi = face_info(rep)
    fam, sty = fi["name"], fi["style"]
    outdir = outroot / f"{fi['tag']}-{rep['size']:02d}pt"
    outdir.mkdir(parents=True, exist_ok=True)
    gl = [g for g in rep["glyphs"] if "box" in g]
    undefined = [label(g) for g in rep["glyphs"] if g["charinfo"]["a"] != 0]
    # blank B0-CF boxes can outgrow a rect sized from their tiny charinfo width;
    # they have no ink and are left out of the fonts, so only inked glyphs count
    clipped = [label(g) for g in gl if g["touches_rect_edge"] and g["ink_pixels"]]
    clamped = [label(g) for g in rep["glyphs"] if g["flags"]]
    plain = [g for g in gl if not g.get("accent")]
    fits = [u / 10 for u in range(150, 401) if plain and all(
        abs(g["charinfo"]["width"] / (u / 10) - g["advance_px"]) <= 0.5 for g in plain)]
    problems = []
    if not rep["complete"]:
        problems.append("INCOMPLETE file (no END record): delete it and run the capture again for this font/size")
    if clipped:
        problems.append("box touches the capture edge (may be clipped): " + " ".join(clipped))
    if clamped:
        problems.append("capture rect clamped: " + " ".join(clamped))
    infont = font_glyphs(rep)
    print(f"{path.name}: {fam} {sty} {rep['size']}pt id={rep['font_id']:04X} drawn={len(gl)} "
          f"in font={len(infont)} undefined={len(undefined)} time~{rep.get('dump_seconds', '?')}s complete={rep['complete']}")
    print("   screen advances vs 1/1800\" widths: "
          + (f"box width = round(width/s) for s = {fits[0]:.1f}..{fits[-1]:.1f}" if fits else
             "hand-tuned (no single scale; e.g. digits) -- box width is the screen advance, "
             "1/1800\" widths kept as print metrics"))
    for p in problems:
        print("   PROBLEM: " + p)
    notes = []
    if gl:
        write_bdf(rep, outdir / f"{fi['stem']}-{rep['size']}.bdf", raw)
        for msg in (write_ttf(rep, outdir / f"{fi['stem']}-{rep['size']}.ttf", raw), write_pngs(rep, outdir)):
            if msg:
                notes.append(msg)
                print("   note: " + msg)
    meta = {k: rep[k] for k in ("face", "size", "font_id", "styles_defined", "style", "complete", "sources") if k in rep}
    meta.update(family=fam, style_name=sty, tag=fi["tag"], font_family=fi["family"], family_file=fi["family_file"],
                list_entry=rep.get("list_entry"), typo_info=rep.get("info"),
                dump_seconds=rep.get("dump_seconds"), scale_fit_units_per_px=[fits[0], fits[-1]] if fits else None,
                undefined_codes=undefined, problems=problems,
                encoding="raw Rosanne codes" if raw else "Unicode (ROSANNE_TO_UNICODE, from the glyphs; PUA U+E000+code otherwise)",
                advance_mode=ADVANCE["mode"], wp_units_per_px=ADVANCE["upp"],
                accents={f"{k:02X}": v[0] for k, v in ACCENTS.items()},
                glyphs=[{"code": g["code"], "accent": g.get("accent", 0), "label": label(g),
                         "unicode": f"U+{unicode_for(g, raw):04X}", "in_font": g in infont, "charinfo": g["charinfo"],
                         "advance_wp_px": round(g["charinfo"]["width"] / ADVANCE["upp"], 3),
                         "draw": g["draw"], **{k: g[k] for k in ("box", "advance_px", "ink_pixels", "box_solid",
                                                              "touches_rect_edge", "box_rows") if k in g}}
                        for g in rep["glyphs"]])
    (outdir / "metadata.json").write_text(json.dumps(meta, indent=1) + "\n")
    return not problems


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inputs", nargs="+", type=Path, help="capture files or folders holding them")
    ap.add_argument("--out", type=Path, default=Path("fonts-out"))
    ap.add_argument("--raw-encoding", action="store_true")
    ap.add_argument("--advance", choices=("wp", "box"), default="wp",
                    help="wp: PcW16 Word Processor spacing from the 1/1800 in widths (default); "
                         "box: the raster box width")
    ap.add_argument("--wp-units-per-px", type=float, default=WP_UNITS_PER_PX)
    ap.add_argument("--family-master", type=int, default=12,
                    help="point size whose glyphs become the installable family fonts (default 12)")
    ap.add_argument("--family-sizes", default="",
                    help="comma-separated sizes for alternate family sets in family/<NN>pt/ (same font names)")
    ap.add_argument("--family-prefix", default="PcW16",
                    help="prefix of every font and file name (default PcW16)")
    a = ap.parse_args()
    ADVANCE.update(mode=a.advance, upp=a.wp_units_per_px)
    FAMILY_PREFIX["prefix"] = a.family_prefix
    files = []
    for p in a.inputs:
        if not p.exists():
            sys.exit(f"{p}: no such file or folder")
        files += [q for q in sorted(p.iterdir()) if q.suffix.upper() in (".FD4", ".FD5", ".FD6")] if p.is_dir() else [p]
    if not files:
        sys.exit("no .FD4 / .FD5 / .FD6 capture files found")
    groups, names = {}, {}
    for f in files:
        try:
            r = parse(f.read_bytes())
        except ValueError as e:
            sys.exit(f"{f}: {e}")
        groups.setdefault((r["font_id"], r["style"] & 3, r["size"]), []).append(f)
        names.setdefault(face_info(r)["name"], set()).add(r["font_id"])
    for name, ids in names.items():   # two listed fonts with one name: tell them apart by ID
        if len(ids) > 1:
            NAME_OVERRIDE.update({i: f"{name} {i:04X}" for i in ids})
    ok = True
    for key in sorted(groups):
        ok &= convert(groups[key], a.out, a.raw_encoding)
    # one installable font per face: "<prefix> <Name>" in the styles that were
    # captured, outlines from the --family-master size. No style is synthesised.
    extra = {int(s) for s in a.family_sizes.split(",") if s.strip()}
    faces = sorted({k[:2] for k in groups})
    for fid, style in faces:
        if (fid, style, a.family_master) not in groups:
            rep = parse(groups[next(k for k in sorted(groups) if k[:2] == (fid, style))][0].read_bytes())
            print(f"note: no {a.family_master}pt capture of {face_info(rep)['family']} {face_info(rep)['style']}: "
                  "no family font for it (choose another size with --family-master)")
    for (fid, style, size), paths in sorted(groups.items()):
        dirs = ([a.out / "family"] if size == a.family_master else []) + \
               ([a.out / "family" / f"{size:02d}pt"] if size in extra else [])
        rep = merge(paths) if dirs else None
        if rep and not rep["complete"]:
            print(f"note: {face_info(rep)['family']} {face_info(rep)['style']} {size}pt is incomplete: no family font")
            continue
        for fam_dir in dirs:
            fi = face_info(rep)
            fam_dir.mkdir(parents=True, exist_ok=True)
            msg = write_ttf(rep, fam_dir / f"{fi['family_file']}.ttf", a.raw_encoding, family=fi["family"])
            print(f"family font: {fam_dir}/{fi['family_file']}.ttf" + (f" ({msg})" if msg else ""))
    (a.out / "rosanne-to-unicode.json").write_text(json.dumps(
        {f"{k:02X}": f"U+{v:04X}" for k, v in sorted(ROSANNE_TO_UNICODE.items())}, indent=1) + "\n")
    print(f"wrote {a.out}/")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
