# Capture file formats

All capture files are little-endian binary files written in the current Rosanne folder. Each file is an 8-byte magic string, an 8-byte header, then a sequence of records. Each record is a 4-character tag, a 16-bit length and that many bytes of payload.

| Version | Written by | Files |
|---|---|---|
| 6 | `FONTCAP.PRG` | `F<id><style><size>.FD6`: one per typeface, style and size; every code and every accent combination |
| 4 | `FONTDMP4.PRG` | `FD4<face><size>.FD4`: Times/Times Bold/Swiss, codes 20-CF |
| 5 | `FONTDMP5.PRG` | `FD5<face><size>.FD5`: Times/Times Bold/Swiss, codes 01-1F and D0-FF, and the accent combinations |

`tools/fdconvert.py` reads all three, groups them by font ID, style and size, and merges an FD4 and FD5 pair into one font. Versions 1 to 3 were diagnostic formats used while developing the method. No tool here reads them.

# Version 6: `F<id><style><size>.FD6` (FONTCAP.PRG)

**Name:** `F`, the typeface ID as 4 hex digits, a style letter (`N` Normal, `B` Bold, `I` Italic, `J` Bold Italic), the size as 2 decimal digits. For example `F0100B12.FD6` is ID `#0100` Bold 12pt.

### Header (16 bytes)

| Off | Size | Meaning |
|---|---|---|
| 0 | 8 | `P16FONT6` |
| 8 | 1 | Version (6) |
| 9 | 1 | Stage (4) |
| 10 | 1 | Position of the typeface in the `os_typo_getlist` list (0 = first) |
| 11 | 1 | Point size |
| 12 | 2 | Font ID passed to `os_typo_def` |
| 14 | 1 | D passed to `os_typo_def`: the list entry's styles, with bit 0 set |
| 15 | 1 | Style drawn: bit 0 = Bold, bit 1 = Italic. Passed to `os_typo_charscreen` in IX lo; bit 0 only is passed to `os_typo_charinfo` in D. |

### Records

The order is:

1. `FACE`, `INFO`, `TIM0`;
2. one `GLY4` for each code `#01` to `#FF` with accent 0;
3. for each accent `#D0` to `#DF` in turn, one `GLY4` for each of the bases space, `A`–`Z`, `a`–`z`, `#91`–`#94`, `#9B` and `#9D`;
4. `TIM1`, `END `.

That makes 255 + 944 = 1,199 `GLY4` records. A file without `END ` is incomplete.

`FACE`, `INFO`, `TIM0`/`TIM1` and `GLY4` are as in version 4 below, except:

* **`FACE`:** the list entry is that of the typeface captured. Its name gives the font name.
* **`GLY4` offset 1:** the accent code (0 = none).
* **`GLY4` offset 13 (flags):**
  * bit 0: the rect's height was clamped to 144 rows;
  * bit 1: its width was clamped to 20 bytes;
  * bit 2: the rows above the baseline were clamped to 136;
  * bit 3: the rows below it were clamped to 56.

**Capture rect:** the margins are:

* across: 3 + size/8 px on each side, plus size/4 more for Italic styles;
* vertically: 2 + size/4 rows above the maximum ascender and below the maximum descender (`os_typo_info`, at 22 units per pixel).

The limits are 20 bytes × 144 rows, at most 136 rows above the baseline and 56 below. That's the drawing area: origin (160, 200) in a clip window x 112–399, y 64–255.

# Version 4: `FD4<face><size>.FD4` (FONTDMP4.PRG, Stage 3)

There is one file per face and size. `FD4TN012.FD4` is Times Normal 12pt; `TB` is Times Bold and `SN` is Swiss Normal. The size is three digits.

### Header (16 bytes)

| Off | Size | Meaning |
|---|---|---|
| 0 | 8 | `P16FONT4` |
| 8 | 1 | Version (4) |
| 9 | 1 | Stage (3) |
| 10 | 1 | Face: 0 Times Normal, 1 Times Bold, 2 Swiss Normal |
| 11 | 1 | Point size |
| 12 | 2 | Font ID passed to `os_typo_def` |
| 14 | 1 | D passed to `os_typo_def`: the list entry's styles, with bit 0 set |
| 15 | 1 | Style used by `charscreen` (IX lo) and `charinfo` (D): bit 0 = Bold |

### Records

The order is `FACE`, `INFO`, `TIM0`, one `GLY4` per code from `#20` to `#CF`, `TIM1`, then `END `.

**`FACE` (43 bytes)**

| Off | Size | Meaning |
|---|---|---|
| 0 | 37 | The 37-byte list entry |
| 37 | 1 | `os_typo_def` A |
| 38 | 1 | Its F |
| 39 | 1 | 1 if `os_typo_init` was called this run |
| 40 | 1 | F after `os_typo_init` |
| 41 | 1 | Slot used |
| 42 | 1 | List source: `C` = `os_copy_24bit`, `M` = mapped read, 0 = none |

**`INFO` (11 bytes):** `os_typo_info` at this face and size: A (1 byte), HL (2 bytes, the address Rosanne returned), then 8 bytes copied from HL: line pitch, maximum ascender, maximum descender and widest character, each a 16-bit word in 1/1800". The 8 bytes are only meaningful when A = 0.

**`TIM0` and `TIM1` (4 bytes each):** `bios_gettime` E (ticks), D (seconds), C (minutes) and B (hours), taken before and after the glyphs. The tick byte turned out not to be a 1/256 s counter (XAnne run 5), so the converter uses whole seconds only.

**`GLY4`:** a 28-byte header, followed by the two captures when the character is defined.

| Off | Size | Meaning |
|---|---|---|
| 0 | 1 | Character code |
| 1 | 1 | Accent (0) |
| 2 | 1 | Style |
| 3 | 1 | `os_typo_charinfo` A (5 = undefined in this font: header only, no captures) |
| 4 | 1 | Its F |
| 5 | 2 | Width, 1/1800" (`os_typo_charinfo` DE) |
| 7 | 2 | Height, 1/1800" (HL, **signed**) |
| 9 | 2 | Baseline height, 1/1800" (BC, **signed**: negative for characters below the baseline, such as `_`) |
| 11 | 1 | `charscreen` A for the W render (#FF = not drawn) |
| 12 | 1 | `charscreen` A for the K render (#FF = not drawn) |
| 13 | 1 | Flags: bit 0 = rect height clamped to 128 rows, bit 1 = width clamped to 16 bytes |
| 14 | 4 | Glyph origin x, y (y = baseline) |
| 18 | 8 | Capture rect x, y, w, h. w = bytes per row × 8. |
| 26 | 1 | Bytes per row |
| 27 | 1 | Reserved |
| 28 | n | **W** capture: white ground; n = bytes per row × h. `bios_getpxl`, bit 1 = white, bit 7 = leftmost. |
| 28 + n | n | **K** capture: black ground |

**How the rect is sized:** x starts at origin − 3 and covers ceil(charinfo width ÷ 22) + 6 pixels, rounded up to whole bytes. y runs from the baseline − (ceil(max ascender ÷ 22) + 2) to the baseline + ceil(max descender ÷ 22) + 2. 22 units/px is below the measured 23.4–26.1, so the rect is oversized on purpose.

**What the converter takes from the captures:**

* **Ink:** the black pixels of W.
* **Glyph box:** the bounding box of the K white pixels together with the ink.
* **Advance:** the box width.
* **Possible clipping:** a box touching the rect edge is flagged.

# Version 5: `FD5<face><size>.FD5` (FONTDMP5.PRG, Stage 3b, optional)

Identical to version 4 except in three ways:

* **Magic and version:** `P16FONT5`, version 5.
* **GLY4 offset 1 (accent)** is the accent code passed in B to `os_typo_charinfo` and `os_typo_charscreen`, or 0 for none.
* **Record order:**
  1. single codes `#01`–`#1F`, then `#D0`–`#FF`, all with accent 0;
  2. then, for each accent `#D0`–`#DF` in turn, the bases space, `A`–`Z`, `a`–`z`, `#91`–`#94`, `#9B` and `#9D`.

  That makes 79 + 944 = 1,023 GLY4 records per file.

**FONTDMP5 capture rect.** The margins grow with the size:

* across: 3 + size/8 px on each side;
* vertically: 2 + size/4 rows above the maximum ascender and below the maximum descender.

This leaves room for accents that overhang narrow letters and for under-accents on descenders. The limits are 14 bytes × 144 rows. GLY4 flags bits 0 and 1 still report any clamping.
