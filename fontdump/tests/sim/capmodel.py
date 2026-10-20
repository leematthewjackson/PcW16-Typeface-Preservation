# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Lee Matthew Jackson - PcW16ers.net & leematthewjackson.com
"""Rosanne mock for FONTCAP: any number of installed fonts, each with its
own ID, styles, RTF family, name, sizes and defined characters; Italic
drawn as a shear; scripted alert answers. Engineering aid only, NOT
evidence about Rosanne. All glyphs are synthetic patterns.
"""
import struct

import z80sim  # noqa: E402  (the caller puts the Z80 model's directory on sys.path)
from rosanne_mock import APP, FLAG_C, LIST_ADDR, LIST_BANK, Model

ALL_SIZES = (6, 8, 10, 11, 12, 14, 18, 24, 36, 72)
TIMES = dict(id=0x0100, styles=0x03, fam=1, name=b"Times", sizes=ALL_SIZES, chars=None)
SWISS = dict(id=0x0101, styles=0x01, fam=2, name=b"Swiss", sizes=ALL_SIZES, chars=None)


class CapModel(Model):
    def setup_fonts(self, fonts, menu=0, sizes=0, per_font=(), **kw):
        """fonts: list of dicts (id, styles, fam, name, sizes, chars: None =
        the base mock's character set, else a set of defined single codes,
        accents then undefined). Alert answers: menu (0 capture, 1 list),
        sizes (0 12pt, 1 6-24pt, 2 all), per_font (one per font alert)."""
        self.fontcfg = fonts
        self.answers = {"menu": menu, "sizes": sizes}
        self.per_font = list(per_font)
        self.alert_buttons_log = []
        self.setup(full=True, known_ids=tuple(f["id"] for f in fonts), **kw)

    def font(self, fid=None):
        fid = self.slots[self.cur][1] if fid is None else fid
        return next(f for f in self.fontcfg if f["id"] == fid)

    def place_list(self, present):
        blk = self.banks[LIST_BANK]
        data = b"".join(struct.pack("<HBB", f["id"], f["styles"], f["fam"]) + f["name"].ljust(33, b"\0")
                        for f in self.fontcfg)
        blk[LIST_ADDR:LIST_ADDR + len(data)] = data if present else b"\xff" * len(data)
        if self.q2 == LIST_BANK:
            self.mem[0x8000:0xC000] = blk

    def cap_glyph(self, code, style, acc=0):
        """(rows, rows above baseline, x offset, advance px) or None, for the
        font in the current slot. Italic (style bit 1): each row shifted right
        by (rows above the baseline - row) // 3 px."""
        f = self.font()
        if f["chars"] is not None and (acc or code not in f["chars"]):
            return None
        g = self.glyph_ex(code, style & 1, acc)
        if g is None or not style & 2:
            return g
        rows, base, xoff, adv = g
        sh = [max(0, (base - r) // 3) for r in range(len(rows))]
        w = len(rows[0]) + max(sh) if rows else 0
        rows = ["." * s + row + "." * (w - s - len(row)) for s, row in zip(sh, rows)]
        return rows, base, xoff, adv

    def os(self, fn):
        if fn == 84:
            self.b, self.c, self.h, self.l = len(self.fontcfg), LIST_BANK, 0x56, 0x2B
            return
        if fn == 87:
            assert self.d & 1, "os_typo_def with bit 0 of D clear"
            f = next((f for f in self.fontcfg if f["id"] == self.hl), None)
            if self.slots.get(self.cur):
                self.a = 8
            elif not self.initialised or f is None:
                self.a = 1
            elif self.b not in f["sizes"]:
                self.a = 2
            else:
                self.slots[self.cur] = ("ours", self.hl, self.b, self.d)
                self.defs.append((self.hl, self.d, self.b))
                self.a = 0
            return
        if fn == 76:
            assert self.c == APP
            text = self._alert_text()
            buttons = self._alert_buttons()
            self.alert_log.append(text)
            self.alert_buttons_log.append(buttons)
            if text.startswith("FONTCAP: preserve"):
                ans = self.answers["menu"]
            elif text.startswith("FONTCAP: which sizes"):
                ans = self.answers["sizes"]
            elif text.startswith("Font ") and len(buttons) > 1:
                ans = self.per_font.pop(0) if self.per_font else 0
            else:
                ans = 0
            assert 0 <= ans < len(buttons), (text, buttons, ans)
            self.poison("bcdehlx")
            self.a, self.f = ans, self.f & ~FLAG_C
            return
        if fn == 92:
            assert self.slots.get(self.cur)
            assert not self.d & 0xFE, "charinfo D: only bit 0 (Bold) is defined"
            g = self.cap_glyph(self.c, self.d & 1, self.b)
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
        if fn == 93:
            assert self.mouse < 0 and self.slots.get(self.cur)
            assert self.ix & 0xFF00 == 0 and self.ix & 0xFF in (0, 1, 2, 3)
            g = self.cap_glyph(self.c, self.ix & 3, self.b)
            if g is None:
                self.a = 5
                return
            rows, base, xoff, _ = g
            for r, row in enumerate(rows):
                for k, ch in enumerate(row):
                    self.put(self.de + xoff + k, self.hl - base + r, 0 if ch == "#" else 1, clip=True)
            self.a = 0
            return
        return super().os(fn)


def run(cpu, limit=6_000_000_000):
    try:
        while True:
            cpu.step()
            if cpu.steps > limit:
                raise z80sim.SimRunaway(f"PC={cpu.pc:04X}")
    except z80sim._SimStop:
        pass
    return cpu
