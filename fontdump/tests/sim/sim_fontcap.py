#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Lee Matthew Jackson - PcW16ers.net & leematthewjackson.com
"""Static execution test of FONTCAP.PRG on a Z80 model with a Rosanne mock
(capmodel.py): any number of fonts, Italic styles, missing sizes, fonts
that define only some codes, resumed runs, an uninitialised typo system.
Engineering aid only, NOT evidence about Rosanne. All glyphs are synthetic.

  python3 sim_fontcap.py PATH/TO/z80sim-dir PATH/TO/FONTCAP.PRG
"""
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(Path(sys.argv[1]).resolve()))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent / "tools"))
import fdconvert  # noqa: E402
from capmodel import ALL_SIZES, SWISS, TIMES, CapModel, run  # noqa: E402

PRG = Path(sys.argv[2]).read_bytes()
TOOLS = HERE.parent.parent / "tools"
BASES = [0x20] + list(range(0x41, 0x5B)) + list(range(0x61, 0x7B)) + [0x91, 0x92, 0x93, 0x94, 0x9B, 0x9D]
ORDER = [(c, 0) for c in range(0x01, 0x100)] + [(b, a) for a in range(0xD0, 0xE0) for b in BASES]
COURIER = dict(id=0x0123, styles=0x05, fam=0, name=b"Courier New", sizes=(10, 12, 24), chars=set(range(0x20, 0x7F)))
DISPLAY = dict(id=0x0200, styles=0x01, fam=0, name=b"Display", sizes=(36, 72), chars=None)
EMPTY = dict(id=0x0300, styles=0x01, fam=0, name=b"No Sizes", sizes=(), chars=None)
failed = False


def check(cond, msg):
    global failed
    print(("PASS " if cond else "FAIL ") + msg)
    failed |= not cond


def restored(cpu):
    return (cpu.mouse == 0 and (cpu.ink, cpu.mode) == (1, 2) and cpu.window == (0, 0, 639, 479)
            and cpu.cur == 1 and all(v is None for v in cpu.slots.values()) and not cpu.draw_outside)


def model_glyphs_ok(cpu, name, data, font):
    rep = fdconvert.parse(bytes(data))
    order = [(g["code"], g["accent"]) for g in rep["glyphs"]]
    ok = rep["complete"] and rep["version"] == 6 and order == ORDER and rep["font_id"] == font["id"]
    sim = CapModel.__new__(CapModel)
    sim.fontcfg, sim.wide_accents = [font], False
    sim.slots, sim.cur = {0: (0, font["id"], rep["size"], 0)}, 0
    bad = []
    for g in rep["glyphs"]:
        e = sim.cap_glyph(g["code"], rep["style"], g["accent"])
        if e is None:
            if g["charinfo"]["a"] != 5 or "box" in g:
                bad.append(fdconvert.label(g))
            continue
        rows, base, xoff, _ = e
        if (g.get("box_rows") != rows or g["box"]["top"] != base or g["box"]["left"] != xoff
                or g["touches_rect_edge"] or g["flags"]):
            bad.append(fdconvert.label(g))
    check(ok and not bad, f"{name}: complete v6, 255 singles + 944 combinations in order, "
                          f"every glyph equals the model, none at the rect edge {bad[:6]}")
    return rep


# 1. List only: FONTLIST.TXT, one OK alert per font, nothing drawn or captured
fonts = [TIMES, SWISS, COURIER, DISPLAY, EMPTY]
cpu = CapModel(PRG)
cpu.setup_fonts(fonts, menu=1)
run(cpu)
check(restored(cpu) and list(cpu.files) == ["FONTLIST.TXT"], f"list only: state restored, only FONTLIST.TXT {list(cpu.files)}")
txt = bytes(cpu.files["FONTLIST.TXT"]).decode()
print("   " + txt.replace("\r\n", "\n   ").rstrip())
want_lines = ["Font 1 of 5: Times  ID=0100 RTF=1 | Styles 03: Normal Bold.  Sizes: 6 8 10 11 12 14 18 24 36 72",
              "Font 3 of 5: Courier New  ID=0123 RTF=0 | Styles 05: Normal Italic.  Sizes: 10 12 24",
              "Font 4 of 5: Display  ID=0200 RTF=0 | Styles 01: Normal.  Sizes: 36 72",
              "Font 5 of 5: No Sizes  ID=0300 RTF=0 | Styles 01: Normal.  Sizes: none"]
check(txt.startswith("FONTCAP font list. getlist entries=5 source=C valid fonts=5")
      and all(w + "\r\n" in txt for w in want_lines), "FONTLIST.TXT: every font with ID, RTF family, styles, probed sizes")
check([b for b in cpu.alert_buttons_log[1:6]] == [["OK"]] * 5 and "FONTLIST.TXT=W" in cpu.alert_log[-1],
      "list only: five per-font alerts with OK only; summary says FONTLIST.TXT written")
check(len(cpu.defs) == 1 + 10 + 10 + 3 + 2,
      f"one test definition, then one os_typo_def per available size in the probe ({len(cpu.defs)})")

# 2. Cancel: nothing touched
cpu = CapModel(PRG)
cpu.setup_fonts(fonts, menu=2)
run(cpu)
check(not cpu.files and not cpu.defs and len(cpu.alert_log) == 1, "Cancel: no file, no font defined, one alert")

# 3. Capture 12pt: Times yes, Swiss skip, Courier yes, Display yes (no 12pt);
# "No Sizes" gets OK only. FONTLIST.TXT exists already: left alone.
cpu = CapModel(PRG)
cpu.setup_fonts(fonts, menu=0, sizes=0, per_font=[0, 1, 0, 0], files={"FONTLIST.TXT": bytearray(b"keep")})
run(cpu)
names = sorted(cpu.files)
check(restored(cpu) and names == ["F0100B12.FD6", "F0100N12.FD6", "F0123I12.FD6", "F0123N12.FD6", "FONTLIST.TXT"]
      and cpu.files["FONTLIST.TXT"] == b"keep", f"12pt: Times N/B and Courier N/I written, FONTLIST.TXT kept {names}")
check(cpu.alert_buttons_log[5] == ["OK"] and "chosen=03" in cpu.alert_log[-2] and "no-size=01" in cpu.alert_log[-2]
      and "written=04" in cpu.alert_log[-2] and "FONTLIST.TXT=E" in cpu.alert_log[-1],
      "summary: chosen=03, written=04, no-size=01 (Display has no 12pt), FONTLIST.TXT=E")
print("   " + " | ".join(cpu.alert_log[-2:]))
caps = {n: cpu.files[n] for n in names if n.endswith(".FD6")}
for n, data in caps.items():
    model_glyphs_ok(cpu, n, data, TIMES if n.startswith("F0100") else COURIER)

# 4. Convert those captures
with tempfile.TemporaryDirectory() as t:
    t = Path(t)
    for n, data in caps.items():
        (t / n).write_bytes(bytes(data))
    r = subprocess.run([sys.executable, "-I", str(TOOLS / "fdconvert.py"), str(t), "--out", str(t / "out")],
                       capture_output=True, text=True)
    print("   " + r.stdout.replace("\n", "\n   ").rstrip()[:1500])
    check(r.returncode == 0, "fdconvert: FD6 files convert without problems")
    from fontTools.ttLib import TTFont  # noqa: E402
    dirs = sorted(p.name for p in (t / "out").iterdir() if p.is_dir())
    check(dirs == ["CourierNew-Italic-12pt", "CourierNew-Regular-12pt", "Times-Bold-12pt", "Times-Regular-12pt", "family"],
          f"one folder per font, style and size {dirs}")
    f = TTFont(str(t / "out" / "family" / "PcW16CourierNew-Italic.ttf"))
    check(f["name"].getDebugName(1) == "PcW16 Courier New" and f["name"].getDebugName(2) == "Italic"
          and f["OS/2"].fsSelection & 0x01 and f["head"].macStyle & 2 and len(f.getBestCmap()) == 95,
          "family font PcW16 Courier New Italic: italic flags, 95 characters (20-7E)")
    f = TTFont(str(t / "out" / "family" / "PcW16Times-Bold.ttf"))
    check(f["name"].getDebugName(1) == "PcW16 Times" and f["OS/2"].fsSelection & 0x20 and f.getBestCmap().get(0xE9),
          "family font PcW16 Times Bold: bold flags, accented letters mapped")
    v = subprocess.run([sys.executable, "-I", str(TOOLS / "verify_fonts.py"), str(t), "--fonts", str(t / "out")],
                       capture_output=True, text=True)
    check(v.returncode == 0 and "FAIL" not in v.stdout, "verify_fonts: all consistency checks pass\n   "
          + v.stdout.strip().replace("\n", "\n   ")[-300:])

# 5. 6pt to 24pt, resumed: Times and Courier chosen, "Skip the rest" at Display;
# every file but two exists already. Only those two are written, at 6 and
# 24pt, the latter Courier Italic (the widest lean).
existing = {f"F0100{s}{z:02d}.FD6": bytearray(b"keep") for s in "NB" for z in ALL_SIZES if z <= 24}
existing.update({f"F0123{s}{z:02d}.FD6": bytearray(b"keep") for s in "NI" for z in (10, 12, 24)})
del existing["F0100N06.FD6"], existing["F0123I24.FD6"]
cpu = CapModel(PRG)
cpu.setup_fonts(fonts, menu=0, sizes=1, per_font=[0, 1, 0, 2], files=existing)
run(cpu)
new = sorted(n for n in cpu.files if cpu.files[n] != b"keep" and n.endswith(".FD6"))
print("   " + " | ".join(cpu.alert_log[-2:]))
check(restored(cpu) and new == ["F0100N06.FD6", "F0123I24.FD6"] and "skipped(exist)=14" in cpu.alert_log[-2]
      and "chosen=02" in cpu.alert_log[-2] and "no-size=05" in cpu.alert_log[-2],
      f"6-24pt resumed: only the two missing files written, 20 (#14) skipped, Courier's 5 missing sizes counted {new}")
check(len(cpu.alert_log) == 1 + 4 + 1 + 2, "Skip the rest: no alert for the fifth font")
for n in new:
    model_glyphs_ok(cpu, n, cpu.files[n], TIMES if n.startswith("F0100") else COURIER)

# 6. Typo system not initialised (XAnne run 2): junk list, def fails, init once
cpu = CapModel(PRG)
cpu.setup_fonts([TIMES, SWISS], menu=1, needs_init=True, copy_ok=False)
run(cpu)
txt = bytes(cpu.files["FONTLIST.TXT"]).decode()
check(cpu.inits == 1 and "valid fonts=2" in txt and "init=" in txt and "Font 2 of 2: Swiss" in txt,
      "uninitialised: os_typo_init called once, then the list is read")
sys.exit(1 if failed else 0)
