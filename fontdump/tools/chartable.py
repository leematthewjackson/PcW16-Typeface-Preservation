#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Lee Matthew Jackson - PcW16ers.net & leematthewjackson.com
"""Character tables for reconstructed PcW16 fonts: one Markdown file per face
listing every glyph with its picture, Rosanne code, Unicode code point and
name, the PcW16 keystroke (ROSAN283 Appendix A, "Keyboard Typing") and how to
type it on a modern computer.

  python3 chartable.py FONTS_DIR [--size 36]

FONTS_DIR is fdconvert.py's output (it holds Times-Regular-36pt/, family/,
...). The tables are written to FONTS_DIR/family/Characters-<family file>.md
and use the glyph PNGs of --size (default 36pt; else the largest size
captured) as pictures.
"""
import argparse
import json
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fdconvert  # noqa: E402,F401

# PcW16 keystrokes per Rosanne character code, from ROSAN283 Appendix A. They
# belong to the character code, not the font. "?" notes: the printed table
# shows a different character for that code than the Times/Swiss fonts hold,
# or its key name is not legible in the copy we used.
PCW16_KEYS = {
    0x60: "the ` key (top left, above Tab)", 0x7F: "Shift+`",
    0x80: "Ctrl+`", 0x81: "Shift+Ctrl+`", 0x82: "Ctrl+2", 0x83: "Shift+Ctrl+J",
    0x84: "Shift+Ctrl+K", 0x85: "Shift+Ctrl+L", 0x86: "Shift+Ctrl+Y", 0x87: "Shift+Ctrl+;",
    0x88: "Shift+Ctrl+G ?", 0x89: "Shift+Ctrl+D ?", 0x8A: "Shift+Ctrl+H ?", 0x8B: "Shift+Ctrl+S ?",
    0x8C: "Tasks+Up ?", 0x8D: "Tasks+Down ?", 0x8E: "Tasks+Left ?", 0x8F: "Tasks+Right ?",
    0x90: "Shift+Ctrl+B", 0x91: "Shift+Ctrl+9", 0x92: "Ctrl+9", 0x93: "Shift+Ctrl+8", 0x94: "Ctrl+8",
    0x95: "Shift+Ctrl+\\", 0x96: "Shift+Ctrl+T", 0x97: "Shift+Ctrl+C", 0x98: "Shift+Ctrl+Z",
    0x99: "Shift+Ctrl+X", 0x9A: "Shift+Ctrl+P", 0x9B: "Ctrl+0", 0x9C: "the £ key", 0x9D: "Shift+Ctrl+0",
    0x9E: "keypad ×", 0x9F: "Shift+Ctrl+Del (Del above the cursor keys)",
    0xA0: "keypad minus, or Ctrl+-", 0xA1: "keypad ÷", 0xA2: "Ctrl+. (or keypad point)",
    0xA3: "Shift+Ctrl+#", 0xA4: "Shift+Ctrl+Red", 0xA5: "Shift+Ctrl+Green", 0xA6: "Shift+Ctrl+[",
    0xA7: "Shift+Ctrl+]", 0xA8: "Shift+Ctrl+/", 0xA9: "Shift+Ctrl+R", 0xAA: "Shift+Ctrl+E",
    0xAB: "Shift+Ctrl+Q", 0xAC: "Shift+Ctrl+W", 0xAD: "Shift+Ctrl+1", 0xAE: "Shift+Ctrl+,",
    0xAF: "Shift+Ctrl+.",
}
ACCENT_KEYS = {0xD0: "Tasks+`", 0xD1: "Tasks+1", 0xD2: "Tasks+2", 0xD3: "Tasks+3", 0xD4: "Tasks+4",
               0xD5: "Tasks+5", 0xD6: "Tasks+6", 0xD7: "Tasks+7", 0xD8: "Tasks+8", 0xD9: "Tasks+9",
               0xDA: "Tasks+0", 0xDB: "Tasks+-", 0xDC: "Tasks+=", 0xDD: "Tasks+#", 0xDE: "Tasks+[",
               0xDF: "Tasks+]"}


def modern(u):
    """How to type code point u on Linux (GTK/Qt), Windows and macOS."""
    if 0x20 < u < 0x7F:
        return "its own key"
    if u == 0x20:
        return "Space"
    win = f"Alt+0{u}" if 0xA0 <= u <= 0xFF else f"Word: {u:04X} then Alt+X"
    return f"Linux: Ctrl+Shift+U {u:04x} Space · Windows: {win} · macOS: Unicode Hex Input, Option+{u:04X}"


def table(fonts, face, size):
    meta = json.loads((fonts / f"{face}-{size:02d}pt" / "metadata.json").read_text())
    rows = [g for g in meta["glyphs"] if g.get("in_font", "box" in g)]
    out = [f"# {meta['font_family']} {meta['style_name']}: character table", "",
           f"Every character in `{meta['family_file']}.ttf` (and the per-size fonts), as Rosanne drew it "
           f"({size}pt pictures). **PcW16** is the keystroke on the original machine (ROSAN283 Appendix A); "
           "**Modern** is how to type the same character today.", "",
           "A `?` marks a keystroke the manual's table cannot fully confirm: for 88–8B its printed character "
           "differs from the Times/Swiss glyph, and for 8C–8F the key names are not legible.", "",
           "| Glyph | Rosanne | Unicode | Name | PcW16 | Modern |", "|:---:|:---:|:---:|---|---|---|"]
    for g in rows:
        u = int(g["unicode"][2:], 16)
        code, acc = g["code"], g.get("accent", 0)
        lab = g.get("label", f"{code:02X}")
        name = unicodedata.name(chr(u), "Private Use (Rosanne-only)" if u >= 0xE000 else "?").title()
        if acc:
            keys = f"{ACCENT_KEYS.get(acc, '?')} then {chr(code) if code < 0x7F else lab}"
        else:
            keys = PCW16_KEYS.get(code, "its own key" if 0x20 < code < 0x7F else ("Space" if code == 0x20 else ""))
        typed = modern(u) if u < 0xE000 else "not in Unicode: use a character map"
        pic = f"![{lab}](../{face}-{size:02d}pt/glyphs/{lab}.png)"
        out.append(f"| {pic} | {lab.replace('+', ' + ')} | U+{u:04X} `{chr(u) if u < 0xE000 else ''}` | {name} "
                   f"| {keys} | {typed} |")
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("fonts", type=Path)
    ap.add_argument("--size", type=int, default=36)
    a = ap.parse_args()
    (a.fonts / "family").mkdir(parents=True, exist_ok=True)
    faces = {}
    for m in sorted(a.fonts.glob("*-*pt/metadata.json")):
        tag, size = m.parent.name.rsplit("-", 1)
        faces.setdefault(tag, set()).add(int(size[:-2]))
    for tag, sizes in sorted(faces.items()):
        size = a.size if a.size in sizes else max(sizes)
        meta = json.loads((a.fonts / f"{tag}-{size:02d}pt" / "metadata.json").read_text())
        p = a.fonts / "family" / f"Characters-{meta['family_file']}.md"
        p.write_text(table(a.fonts, tag, size))
        print(f"wrote {p}")


if __name__ == "__main__":
    main()
