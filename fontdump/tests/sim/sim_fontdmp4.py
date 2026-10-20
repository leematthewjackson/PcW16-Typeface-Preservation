#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Lee Matthew Jackson - PcW16ers.net & leematthewjackson.com
"""Static execution test of FONTDMP4.PRG (Stage 3) on a Z80 model
(z80sim.py, see README.md) with the Rosanne mock (rosanne_mock.py, full=True:
synthetic glyphs 20-AF, B0-CF undefined, glyphs scaled with the size, bold
one pixel wider). Engineering aid only, NOT evidence about Rosanne.

Usage: python3 sim_fontdmp4.py PATH/TO/z80sim-dir PATH/TO/FONTDMP4.PRG
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
SIZES = (6, 8, 10, 11, 12, 14, 18, 24, 36, 72)
failed = False


def run(**kw):
    cpu = Model(PRG)
    cpu.setup(full=True, **kw)
    try:
        while True:
            cpu.step()
            if cpu.steps > 400_000_000:
                raise z80sim.SimRunaway(f"PC={cpu.pc:04X}")
    except z80sim._SimStop:
        pass
    return cpu


def check(cond, msg):
    global failed
    print(("PASS " if cond else "FAIL ") + msg)
    failed |= not cond


def restored(cpu, name):
    check(cpu.mouse == 0 and (cpu.ink, cpu.mode) == (1, 2) and cpu.window == (0, 0, 639, 479),
          f"{name}: pointer, ink, mode, clip window restored")
    check(cpu.q2 == APP and cpu.cur == 1, f"{name}: quarter 2 and original slot restored")
    check(all(v is None or v == "WP" for v in cpu.slots.values()), f"{name}: our slot released")
    check(not cpu.draw_outside, f"{name}: drawing confined to the drawing area")


sample = Path(__file__).resolve().parent.parent.parent / "build" / "sim-sample" / "fd4"
sample.mkdir(parents=True, exist_ok=True)
for old in sample.glob("*.FD4"):
    old.unlink()

# 1. "12pt only" on a run-2-like system (init needed)
cpu = run(copy_ok=False, map_ok=False, needs_init=True, menu_answer=0)
restored(cpu, "12pt")
names = sorted(n for n in cpu.files if n.endswith(".FD4"))
check(names == ["FD4SN012.FD4", "FD4TB012.FD4", "FD4TN012.FD4"], f"12pt: three files {names}")
check(cpu.inits == 1, "12pt: os_typo_init once (all slots empty, list junk)")
check(sorted(cpu.defs[1:]) == [(0x100, 15, 12), (0x100, 15, 12), (0x200, 15, 12)],
      f"12pt: after the test definition, Times defined with D = list styles (#0F in the mock) twice "
      f"(normal, bold) and Swiss once: {cpu.defs}")
print("   alerts:", " | ".join(cpu.alert_log))
check("written=03" in cpu.alert_log[1] and "failed=00" in cpu.alert_log[1], "12pt: summary alert")
for n in names:
    (sample / n).write_bytes(bytes(cpu.files[n]))
    rep = fd4convert.parse(bytes(cpu.files[n]))
    gl = [g for g in rep["glyphs"] if "box" in g]
    bold = rep["face"] == 1
    check(rep["complete"] and len(rep["glyphs"]) == 0xD0 - 0x20 and len(gl) == 0xB0 - 0x20,
          f"{n}: complete, 176 records, 144 glyphs")
    ok = True
    for g in gl:
        rows, base = cpu.glyph.__func__(type("S", (), {"slots": {0: (0, 0, 12, 0)}, "cur": 0})(), g["code"], bold)
        if g["box_rows"] != rows or g["box"]["top"] != base or g["touches_rect_edge"]:
            ok = False
            print("   mismatch", hex(g["code"]), g["box_rows"], rows)
            break
    check(ok, f"{n}: every glyph's box and ink equal the model's, none at the capture edge")
out = sample.parent / "fd4-out"
r = subprocess.run([sys.executable, "-I", str(TOOLS / "fdconvert.py"), str(sample), "--out", str(out)],
                   capture_output=True, text=True)
print("   " + r.stdout.replace("\n", "\n   ").rstrip())
check(r.returncode == 0 and (out / "Times-Regular-12pt" / "PcW16-Times-Regular-12.bdf").exists()
      and (out / "Times-Bold-12pt" / "sheet.png").exists(), "converter: BDF, sheets, metadata")
ttf = out / "Times-Regular-12pt" / "PcW16-Times-Regular-12.ttf"
if ttf.exists():
    from fontTools.ttLib import TTFont
    f = TTFont(str(ttf))
    check(f["cmap"].getBestCmap()[ord("A")] == "R41" and f["hmtx"]["R41"][0] == round(9 * 24 / fd4convert.WP_UNITS_PER_PX * 64),
          "converter: pixel TTF maps A, WP advance (mock width 9 x 24 units / WP_UNITS_PER_PX)")
r = subprocess.run(["bdftopcf", "-o", str(out / "t.pcf"), str(out / "Times-Regular-12pt" / "PcW16-Times-Regular-12.bdf")],
                   capture_output=True, text=True)
check(r.returncode == 0, "converter: BDF accepted by bdftopcf " + r.stderr.strip())

# 2. "All sizes", resuming: every file exists except Times Normal 6pt and Swiss 18pt
existing = {f"FD4{f}{s:03d}.FD4": bytearray(b"keep") for f in ("TN", "TB", "SN") for s in SIZES}
del existing["FD4TN006.FD4"], existing["FD4SN018.FD4"]
cpu = run(menu_answer=1, files=existing)
restored(cpu, "all sizes")
new = sorted(n for n in cpu.files if cpu.files[n] != b"keep")
check(new == ["FD4SN018.FD4", "FD4TN006.FD4"], f"all sizes: only the two missing files written {new}")
check(all(cpu.files[n] == b"keep" for n in existing), "all sizes: existing files untouched")
print("   alerts:", " | ".join(cpu.alert_log))
check("written=02" in cpu.alert_log[1] and "skipped(exist)=1C" in cpu.alert_log[1], "all sizes: 2 written, 28 skipped")
for n in new:
    rep = fd4convert.parse(bytes(cpu.files[n]))
    gl = [g for g in rep["glyphs"] if "box" in g]
    check(rep["complete"] and len(gl) == 144 and not any(g["touches_rect_edge"] for g in gl),
          f"{n}: complete, 144 glyphs, none clipped")
    (sample / n).write_bytes(bytes(cpu.files[n]))

# 3. Cancel: nothing touched
cpu = run(menu_answer=2)
check(not cpu.files and 85 not in cpu.os_calls and cpu.mouse == 0, "cancel: no files, no slot touched")
sys.exit(1 if failed else 0)
