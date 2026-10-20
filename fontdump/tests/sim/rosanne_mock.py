# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Lee Matthew Jackson - PcW16ers.net & leematthewjackson.com
"""Mock of the Rosanne calls used by the FONTDUMP programs, for a Z80
model (z80sim.py, not included: see tests/sim/README.md). Engineering aid
only, NOT evidence about Rosanne. The glyphs it draws are synthetic
patterns, not PcW16 typefaces. Behaviour follows ROSAN283 plus what XAnne runs 1
and 2 showed (docs/AUDIT.md): list junk until os_typo_init when needs_init,
charscreen y = baseline, getpxl 1 = white.

Opaque charscreen paints a cell (advance x line height) white unless
paint_cell=False -- the open question FONTDMP3's K render answers.
"""
import struct
import sys
from pathlib import Path

import z80sim  # noqa: E402  (the caller puts the Z80 model's directory on sys.path)

APP = 0x8E          # XAnne run 1: the app block, also at quarter 2 at start
LIST_BANK, LIST_ADDR = 0x84, 0x162B
W, H = 640, 480
FLAG_C = 0x01
POISON = 0xA5
A_ROWS = ["....#....", "...#.#...", "...#.#...", "..#...#..", "..#...#..",
          "..#####..", ".#.....#.", ".#.....#.", "##.....##"]
G_ROWS = [".......", ".......", ".......", "..####.", ".#...#.", ".#...#.",
          ".#...#.", "..####.", ".....#.", "#....#.", ".####.."]
I_ROWS = [".#.", "...", "##.", ".#.", ".#.", ".#.", "###"]
# code: (rows from the top, rows above the baseline, advance in pixels)
GLYPHS = {ord("A"): (A_ROWS, 9, 10), ord("g"): (G_ROWS, 8, 7), ord("i"): (I_ROWS, 7, 4), ord(" "): ([], 0, 4)}
CELL_ASCENT, CELL_DESCENT = 13, 4   # model cell: rows above / below the baseline


def font_list():
    out = b""
    for fid, sty, fam, name in ((0x0100, 0x0F, 1, b"Times"), (0x0200, 0x0F, 2, b"Swiss")):
        out += struct.pack("<HBB", fid, sty, fam) + name.ljust(33, b"\0")
    return out


class Model(z80sim.CPU):
    def setup(self, copy_ok=True, map_ok=True, list_ok_after_init=True, needs_init=False,
              known_ids=(0x0100, 0x0200), slots=None, files=None, paint_cell=True,
              full=False, menu_answer=0, wide_accents=False):
        self.wide_accents = wide_accents
        self.paint_cell = paint_cell
        self.full = full                 # Stage 3 model: any size, bold, synthetic glyphs 20-AF
        self.menu_answer = menu_answer
        self.defs = []                   # (id, styles, size) of every successful os_typo_def
        self.copy_ok, self.map_ok = copy_ok, map_ok
        self.list_ok_after_init = list_ok_after_init
        self.initialised = not needs_init
        self.known_ids = known_ids
        self.files = dict(files or {})
        self.open_w = None
        self.screen = bytearray([1]) * (W * H)
        self.ink, self.mode, self.window, self.mouse = 1, 2, (0, 0, 639, 479), 0
        self.slots = dict(slots or {i: None for i in range(16)})
        self.cur = 1
        self.alert_log, self.draw_outside, self.os_calls = [], [], []
        self.inits = 0
        self.q2 = APP
        self.banks = {LIST_BANK: bytearray(b"\xff" * 0x4000)}
        self.q2_mem = bytes(self.mem[0x4000:0x8000])   # app block mirrored at #8000
        self.mem[0x8000:0xC000] = self.q2_mem
        self.place_list(map_ok)

    def glyph_ex(self, code, bold, acc=0):
        """As glyph(), plus (x offset of the rows from the origin, advance px).
        With wide_accents: over-accents D0-DB are 2k px wider than the base
        on each side (overhang), under-accents DC-DF sit k rows below the
        base glyph's lowest row (below a descender)."""
        g = self.glyph(code, bold)
        if not acc or g is None or not getattr(self, "wide_accents", False):
            g2 = self.glyph(code, bold, acc)
            return None if g2 is None else (g2[0], g2[1], 0, len(g[0][0]) if g else len(g2[0][0]))
        if not 0xD0 <= acc <= 0xDF:
            return None
        rows, base = g
        k = max(1, round(self.slots[self.cur][2] / 12))
        w = len(rows[0])
        if acc <= 0xDB:
            ov = 2 * k
            mark = ["#" * (w + 2 * ov)] + ["." * (w + 2 * ov)] * k
            body = ["." * ov + r + "." * ov for r in rows]
            return mark + body, base + len(mark), -ov, w
        under = ["." * w] * k + ["#" * w] * k
        return rows + under, base, 0, w

    def glyph(self, code, bold, acc=0):
        """Stage 3 model glyph at the defined size: (rows, rows above the
        baseline) or None for an undefined code (B0-CF, 01-1F, E0-FF).
        D0-DF alone: a small accent mark. With an accent: the base glyph
        with a two-row mark (pattern from the accent code) above it."""
        if acc:
            g = self.glyph(code, bold)
            if g is None or not 0xD0 <= acc <= 0xDF:
                return None
            rows, base = g
            w = len(rows[0])
            mark = ["".join("#" if (x + acc) % 2 == 0 else "." for x in range(w)), "." * w]
            return mark + rows, base + 2
        if 0xD0 <= code <= 0xDF:
            k = max(1, round(self.slots[self.cur][2] / 12))
            return ["#.#"[:3] * k, ".#." * k], 9
        if code >= 0xB0 or code < 0x20:
            return None
        if code in GLYPHS and code != 0x20:
            rows, base, _ = GLYPHS[code]
        elif code == 0x20:
            rows, base = ["..."], 6
        else:
            w = 3 + code % 5
            rows = ["".join("#" if (x + r + code) % 3 == 0 else "." for x in range(w)) for r in range(7)]
            base = 7
        k = max(1, round(self.slots[self.cur][2] / 12))
        rows = ["".join(c * k for c in row) for row in rows for _ in range(k)]
        if bold:
            rows = ["".join("#" if row[x] == "#" or (x and row[x - 1] == "#") else "." for x in range(len(row)))
                    + ("#" if row[-1] == "#" else ".") for row in rows]
        return rows, base * k

    def place_list(self, present):
        blk = self.banks[LIST_BANK]
        blk[LIST_ADDR:LIST_ADDR + 74] = font_list() if present else b"\xff" * 74
        if self.q2 == LIST_BANK:
            self.mem[0x8000:0xC000] = blk

    def rw(self, a):
        return self.mem[a] | self.mem[(a + 1) & 0xFFFF] << 8

    def put(self, x, y, v, clip=False):
        x0, y0, x1, y1 = (112, 64, 400, 256) if self.full else (96, 96, 160, 160)
        if not (x0 <= x < x1 and y0 <= y < y1):
            self.draw_outside.append((x, y))
        if clip:
            wx, wy, ww, wh = self.window
            if not (wx <= x < wx + ww and wy <= y < wy + wh):
                return
        self.screen[y * W + x] = v

    def poison(self, regs):
        for r in regs:
            if r == "x":
                self.ix = 0xA5A5
            else:
                setattr(self, r, POISON)

    def _call(self, target):
        if target == 0x003B:
            fn = self.a
            self.os_calls.append(fn)
            self.os(fn)
            self.poison(self.CORRUPT.get(fn, ""))
            return
        if target in (0xC8, 0xCB, 0xCE, 0xD1):
            self.a = {0xC8: 0x80, 0xCB: APP, 0xCE: self.q2, 0xD1: 0x90}[target]
            return
        if target == 0xB0:  # bios_gettime: E ticks, D s, C min, B h (model: 4M steps = 1 s)
            t = self.steps // 15625            # ticks of 1/256 s
            self.e, self.d = t % 256, (t // 256) % 60
            self.c, self.b = (t // 15360) % 60, (t // 921600) % 24
            self.f = POISON
            return
        if target == 0xC2:  # bios_setmem2
            if self.q2 in self.banks:
                self.banks[self.q2][:] = self.mem[0x8000:0xC000]
            self.q2 = self.a
            self.mem[0x8000:0xC000] = self.banks[self.a] if self.a in self.banks else self.q2_mem
            return
        if target in (0xE0, 0xE6):
            setattr(self, "ink" if target == 0xE0 else "mode", self.a)
            self.c = POISON
            return
        if target in (0xE3, 0xE9):
            self.a = self.ink if target == 0xE3 else self.mode
            return
        if target == 0xF5:
            assert self.mouse < 0, "getpxl with pointer visible"
            self.a = self.screen[self.hl * W + self.de]
            self.h = self.l = POISON
            return
        if target < 0x4000:
            raise z80sim.SimError(f"unexpected low call {target:04X}h")
        self._push16(self.pc)
        self.pc = target

    CORRUPT = {84: "de", 85: "bcdhl", 86: "bcdhl", 88: "bcdehl", 90: "bcde", 93: "bcdehl",
               117: "bcdehlx", 119: "bde", 83: "bcdehl"}

    def os(self, fn):
        if fn == 23:
            raise z80sim._SimStop()
        if fn == 41:
            n = self.ix
            if self.c == LIST_BANK and not self.copy_ok:
                src = b"\xff" * n
            elif self.c == LIST_BANK:
                src = bytes(self.banks[LIST_BANK][self.hl & 0x3FFF:(self.hl & 0x3FFF) + n])
            elif self.c == 0x80:
                src = bytes(self.mem[self.hl & 0x3FFF:(self.hl & 0x3FFF) + n])
            else:
                raise AssertionError(f"copy from {self.c:02X}")
            assert self.b == APP
            d = 0x4000 + (self.de & 0x3FFF)
            self.mem[d:d + n] = src
            self.ix = 0
            self.f &= ~FLAG_C
            self.a = POISON
            return
        if fn == 76:
            assert self.c == APP
            text = self._alert_text()
            self.alert_log.append(text)
            self.poison("bcdehlx")
            self.a, self.f = (self.menu_answer if "Which sizes" in text else 0), self.f & ~FLAG_C
            return
        if fn == 83:
            assert all(v is None for v in self.slots.values()), "os_typo_init with a slot in use"
            self.inits += 1
            self.initialised = True
            self.slots = {i: None for i in range(16)}
            if self.list_ok_after_init:
                self.copy_ok = True
                self.place_list(True)
            self.f &= ~FLAG_C
            return
        if fn == 84:
            self.b, self.c, self.h, self.l = 2, LIST_BANK, 0x56, 0x2B   # top bits set: must be ignored
            return
        if fn == 85:
            if self.e in self.slots:
                self.cur = self.e
                self.a = 0 if self.slots[self.e] else 4
            else:
                self.a = 3
            return
        if fn == 86:
            self.e = self.cur
            return
        if fn == 87:
            assert self.d & 1 and (self.b == 12 or self.full and self.b in (6, 8, 10, 11, 12, 14, 18, 24, 36, 72))
            if self.slots.get(self.cur):
                self.a = 8
            elif not self.initialised or self.hl not in self.known_ids:
                self.a = 1
            else:
                self.slots[self.cur] = ("ours", self.hl, self.b, self.d)
                self.defs.append((self.hl, self.d, self.b))
                self.a = 0
            return
        if fn == 88:
            self.a = 0 if self.slots.get(self.cur) else 4
            self.slots[self.cur] = None
            return
        if fn == 90:
            k = max(1, self.slots[self.cur][2] / 12) if self.full else 1   # glyphs never shrink below 12pt size
            self.mem[0x2E80:0x2E88] = struct.pack("<4H", int(402 * k), int(294 * k), int(72 * k), int(288 * k))
            self.h, self.l, self.a = 0x2E, 0x80, 0
            return
        if fn == 92:
            assert self.slots.get(self.cur)
            if self.full:
                g = self.glyph_ex(self.c, self.d & 1, self.b)
                if g is None:
                    self.a = 5
                    self.poison("bcdehl")
                    return
                rows, base, _, adv = g
                self.a = 0
                self.d, self.e = 0, adv * 24
                self.h, self.l = 0, 210
                self.b, self.c = 0, base * 24
                return
            rows, base, adv = GLYPHS[self.c]
            self.a = 0
            self.d, self.e = 0, adv * 24
            self.h, self.l = 0, len(rows) * 24
            self.b, self.c = 0, base * 24
            return
        if fn == 91:
            assert self.slots.get(self.cur)
            self.a, self.d, self.e = 0, 0, GLYPHS[self.c][2] * 24
            self.poison("bchl")
            return
        if fn == 93:
            assert self.mouse < 0 and self.slots.get(self.cur)
            if self.full:
                assert self.ix in (0, 1)
                rows, base, xoff, _ = self.glyph_ex(self.c, self.ix & 1, self.b)
                for r, row in enumerate(rows):
                    for k, ch in enumerate(row):
                        self.put(self.de + xoff + k, self.hl - base + r, 0 if ch == "#" else 1, clip=True)
                self.a = 0
                return
            assert self.ix == 0
            rows, base, adv = GLYPHS[self.c]
            if self.paint_cell:
                for yy in range(self.hl - CELL_ASCENT, self.hl + CELL_DESCENT):
                    for xx in range(self.de, self.de + adv):
                        self.put(xx, yy, 1, clip=True)
            for r, row in enumerate(rows):
                for k, ch in enumerate(row):
                    self.put(self.de + k, self.hl - base + r, 0 if ch == "#" else 1, clip=True)
            self.a = 0
            return
        if fn in (111, 112):
            self.mouse += 1 if fn == 112 else -1
            return
        if fn == 117:
            assert self.c == 0x80
            op = self.mem[self.hl]
            x, y, w, h = (self.rw(self.hl + 1 + i) for i in (0, 2, 4, 6))
            for yy in range(y, y + h):
                for xx in range(x, x + w):
                    self.put(xx, yy, 1 if op == 1 else 0)
            self.f &= ~FLAG_C
            self.a = POISON
            return
        if fn == 118:
            self.window = tuple(self.rw(self.hl + i) for i in (0, 2, 4, 6))
            self.f &= ~FLAG_C
            return
        if fn == 119:
            self.mem[0x2F00:0x2F08] = struct.pack("<4H", 0, 0, 639, 479)
            self.c, self.h, self.l = 0x80, 0x2F, 0x00
            return
        if fn in (144, 145, 146):
            return self.file(fn)
        raise z80sim.SimError(f"unexpected OS fn {fn}")

    def lowstr(self, a):
        assert a < 0x4000
        return self.mem[a:self.mem.index(0, a)].decode()

    def file(self, fn):
        if fn == 144:
            name = self.lowstr(self.hl) + self.lowstr(self.de)
            if self.b == 0:
                if name in self.files:
                    self.f &= ~FLAG_C
                else:
                    self.a, self.f = 2, self.f | FLAG_C
            else:
                self.files[name] = bytearray()
                self.open_w = name
                self.f &= ~FLAG_C
        elif fn == 145:
            if self.b == 1:
                self.open_w = None
            self.f &= ~FLAG_C
        else:
            assert self.open_w and self.c == APP and self.b == 0
            assert 0x4000 <= self.hl and self.hl + self.de <= 0x8000
            self.files[self.open_w] += self.mem[self.hl:self.hl + self.de]
            self.f &= ~FLAG_C
        self.poison("bcdehl")


