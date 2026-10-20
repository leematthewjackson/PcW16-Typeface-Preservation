#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Lee Matthew Jackson - PcW16ers.net & leematthewjackson.com
"""Static execution test of FONTDMP5.PRG (Stage 3b: accents, accented
letters, codes 01-1F and D0-FF) on a Z80 model (z80sim.py, see README.md)
with the Rosanne mock (rosanne_mock.py, full=True; accents modelled as a
two-row mark above the base, D0-DF alone as a small mark, 01-1F/E0-FF
undefined). Engineering aid only, NOT evidence about Rosanne.

Usage: python3 sim_fontdmp5.py PATH/TO/z80sim-dir PATH/TO/FONTDMP5.PRG
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(sys.argv[1]).resolve()))
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "tools"))
import z80sim  # noqa: E402
import fdconvert as fd4convert  # noqa: E402
from rosanne_mock import APP, Model  # noqa: E402

PRG = Path(sys.argv[2]).read_bytes()
TOOLS = Path(__file__).resolve().parent.parent.parent / "tools"
SAMPLE4 = Path(__file__).resolve().parent.parent.parent / "build" / "sim-sample" / "fd4"
BASES = [0x20] + list(range(0x41, 0x5B)) + list(range(0x61, 0x7B)) + [0x91, 0x92, 0x93, 0x94, 0x9B, 0x9D]
SINGLES = list(range(0x01, 0x20)) + list(range(0xD0, 0x100))
failed = False


def check(cond, msg):
    global failed
    print(("PASS " if cond else "FAIL ") + msg)
    failed |= not cond


cpu = Model(PRG)
cpu.setup(full=True, menu_answer=0)
try:
    while True:
        cpu.step()
        if cpu.steps > 2_000_000_000:
            raise z80sim.SimRunaway(f"PC={cpu.pc:04X}")
except z80sim._SimStop:
    pass
check(cpu.mouse == 0 and (cpu.ink, cpu.mode) == (1, 2) and cpu.window == (0, 0, 639, 479)
      and cpu.q2 == APP and cpu.cur == 1 and all(v is None for v in cpu.slots.values()) and not cpu.draw_outside,
      "state restored, slot released, drawing confined")
names = sorted(cpu.files)
check(names == ["FD5SN012.FD5", "FD5TB012.FD5", "FD5TN012.FD5"], f"three FD5 files {names}")
print("   alerts:", " | ".join(cpu.alert_log))
check("FONTDMP5 files written=03" in cpu.alert_log[1], "summary alert")
sample = Path(__file__).resolve().parent.parent.parent / "build" / "sim-sample" / "fd5"
sample.mkdir(parents=True, exist_ok=True)
for n in names:
    (sample / n).write_bytes(bytes(cpu.files[n]))
    rep = fd4convert.parse(bytes(cpu.files[n]))
    order = [(g["code"], g["accent"]) for g in rep["glyphs"]]
    want = [(c, 0) for c in SINGLES] + [(b, a) for a in range(0xD0, 0xE0) for b in BASES]
    check(rep["complete"] and rep["version"] == 5 and order == want, f"{n}: complete, 79 singles + 944 combinations in order")
    bold = rep["face"] == 1
    sim = Model.__new__(Model)
    sim.slots, sim.cur = {0: (0, 0, 12, 0)}, 0
    ok = True
    for g in rep["glyphs"]:
        expect = sim.glyph(g["code"], bold, g["accent"])
        if expect is None:
            ok &= g["charinfo"]["a"] == 5 and "box" not in g
        else:
            ok &= g.get("box_rows") == expect[0] and g["box"]["top"] == expect[1] and not g["touches_rect_edge"]
    check(ok, f"{n}: every glyph equals the model (undefined codes header-only)")
out = sample.parent / "fd5-out"
r = subprocess.run([sys.executable, "-I", str(TOOLS / "fdconvert.py"), str(SAMPLE4), str(sample), "--out", str(out),
                    "--family-master", "12"], capture_output=True, text=True)
print("   " + r.stdout.replace("\n", "\n   ").rstrip()[:900])
check(r.returncode == 0, "converter: FD4 + FD5 merged without problems")
from fontTools.ttLib import TTFont  # noqa: E402
f = TTFont(str(out / "Times-Regular-12pt" / "PcW16-Times-Regular-12.ttf"))
cmap = f.getBestCmap()
check(cmap.get(0xE9) == "R65_D1" and cmap.get(0xC5) == "R41_D5" and cmap.get(0xE7) == "R63_DE"
      and cmap.get(0x010F) == "R64_DB" and cmap.get(0x0165) == "R74_DB" and cmap.get(0x010C) == "R43_D4"
      and cmap.get(ord("A")) == "R41",
      "merged TTF maps é, Å, ç; ď/ť from the apostrophe accent, Č from háček; plain A")
check(len(cmap) > 144 + 800 and (out / "Times-Regular-12pt" / "sheet-accents.png").exists(),
      f"merged TTF has the plain and accented glyphs ({len(cmap)} mapped)")
check((out / "family" / "PcW16Times-Regular.ttf").exists(), "family font from the merged set")

# 2. Wide accents at 18pt: over-accents overhang the base by 2k px each side,
# under-accents hang k rows below descenders. FONTDMP4's fixed margins (3 px,
# 2 rows) would clip these; FONTDMP5's size-scaled margins must not.
existing = {f"FD5{f}{s:03d}.FD5": bytearray(b"keep") for f in ("TN", "TB", "SN")
            for s in (6, 8, 10, 11, 12, 14, 18, 24, 36, 72)}
del existing["FD5TN018.FD5"]
cpu = Model(PRG)
cpu.setup(full=True, menu_answer=1, files=existing, wide_accents=True)
try:
    while True:
        cpu.step()
        if cpu.steps > 4_000_000_000:
            raise z80sim.SimRunaway(f"PC={cpu.pc:04X}")
except z80sim._SimStop:
    pass
new = [n for n in cpu.files if cpu.files[n] != b"keep"]
check(new == ["FD5TN018.FD5"] and not cpu.draw_outside, f"wide accents 18pt: only FD5TN018 written {new}")
rep = fd4convert.parse(bytes(cpu.files["FD5TN018.FD5"]))
sim = Model.__new__(Model)
sim.slots, sim.cur, sim.wide_accents = {0: (0, 0, 18, 0)}, 0, True
bad = []
for g in rep["glyphs"]:
    e = sim.glyph_ex(g["code"], False, g["accent"])
    if e is None:
        continue
    rows, base, xoff, _ = e
    if g.get("box_rows") != rows or g["box"]["top"] != base or g["box"]["left"] != xoff or g["touches_rect_edge"]:
        bad.append(fd4convert.label(g))
check(not bad, f"wide accents 18pt: every overhanging / under accent captured whole, none at the edge {bad[:8]}")
sys.exit(1 if failed else 0)
