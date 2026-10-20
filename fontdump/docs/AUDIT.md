# Technical audit and verification status

This records what has been verified, how, and what still needs testing. Evidence levels:

| Level | Meaning |
|---|---|
| **R: Rosanne** | Observed running under Rosanne in the XAnne emulator (development runs 1–7, below) |
| **G: genuine output** | Compared with output Rosanne produced in normal use: PcW16 Word Processor screenshots |
| **C: consistency** | The generated fonts hold exactly what was captured (`tools/verify_fonts.py`). This cannot detect a wrong capture. |
| **S: simulator** | Program logic run on a Z80 model with a Rosanne mock (`tests/sim/`). **Not evidence of Rosanne behaviour.** |
| **A: assumption** | Inferred, not yet tested |

## 1. Development evidence (XAnne)

The method was developed and verified in seven XAnne runs on one standard installation. The raw evidence (capture files, screenshots) holds typeface artwork and isn't published. Its findings were:

| Run | Program | Finding | Level |
|---|---|---|---|
| 1–3 | diagnostic programs (not included) | `bios_getpxl` reads the screen exactly. `bios_getbitmap` never filled the caller's buffer, so it isn't used. | R |
| 2 | 〃 | Under File Manager the typeface list behind `os_typo_getlist` is junk until `os_typo_init` is called. After that the list is valid and stays valid. With all slots empty, `os_typo_init` is safe. | R |
| 2 | 〃 | The list had two entries: ID `#0100` "Times", styles `#03` (Normal, Bold), RTF family 1; ID `#0101` "Swiss", styles `#01`, RTF family 2. Times Bold is a style of Times, not a separate entry. | R |
| 3 | 〃 | `os_typo_charscreen`: y is the baseline, x the origin; opaque mode paints the glyph's raster box. Drawing on black therefore shows the box. | R |
| 4, 5 | `FONTDMP4.PRG` | All 30 face/size combinations (Times, Times Bold, Swiss × 6–72pt), codes `#20`–`#CF`, captured completely. No inked glyph touched its capture rect. 12pt was identical across runs 4 and 5. | R |
| 5 | 〃 | Two 72pt Word Processor screenshots: every letter's ink is **identical** to the captured glyph, and every screenshot pixel is accounted for. The Word Processor positions letters by the accumulated 1/1800" widths at 24.15–24.20 units per pixel; the converter uses 24.175. | G |
| 6 | `FONTDMP5.PRG` | All 30 face/size combinations: the 16 accents, all 944 accent combinations, and codes `#01`–`#1F` and `#E0`–`#FF` (all blank). Complete and unclipped. The accent order matches the converter's table. i and j lose their dot under accents; narrow letters shift right under wide accents; under-accents stay at a fixed height. | R |
| 6 | 〃 | The Word Processor's Select Character dialog offers the same 16 accents over any character. | R |
| 7 | `FONTCAP.PRG` (this package) | **List mode:** both typefaces, IDs, styles, RTF families and all ten sizes found; `FONTLIST.TXT` written; every alert as expected. | R |
| 7 | 〃 | **Capture:** 12pt, then all sizes, 30 files. All complete, with no glyph at its rect edge and none clamped. All 33 fonts built from them (30 per size plus 3 family) are identical to the fonts from runs 5 and 6: outlines, advances, character maps, line gaps, BDF bitmaps. Every glyph is identical to run 6's captures, and every inked glyph to run 5's. | R, C |
| 7 | 〃 | **Resume:** existing files were skipped and left byte-identical; a deleted file was recaptured identically. **Time:** about 25 minutes of emulated time for all 30 files at 500 %. | R |

**`charinfo` returns signed values.** HL and BC from `os_typo_charinfo` must be read as signed: the underscore's baseline height is negative. Level R.

**Function numbers.** One emulator's source (JoyceAnne, `AnneAccel.cxx`) labels OS function `0x5B` as `os_typo_charinfo` and `0x5C` as `os_typo_charwidth`; this toolkit calls charinfo as 92 (`0x5C`). Resolution:

* the Rosanne include files number the calls from 1, giving `os_typo_charwidth` = 91 and `os_typo_charinfo` = 92;
* the emulator's labels are debug text only, with no effect on behaviour;
* over 4,290 captured glyphs, call 92's DE, HL and BC match the captured box width, ink top and ink bottom (correlation 0.994, 0.996 and 0.945). A corrupted register could not do that.

The toolkit's numbering is correct. Levels R and C.

## 2. Verification of this package

| Check | Result | Level |
|---|---|---|
| `FONTDMP4.PRG` and `FONTDMP5.PRG`, rebuilt from the sources here | Byte-identical to the programs used in runs 4–6 (SHA-256 in `MANIFEST.md`) | C |
| `tools/fdconvert.py` on the private run 5 and 6 captures | All 30 per-size TTF and BDF fonts and the 3 family fonts have glyphs, advances, character maps and line gaps identical to the accepted fonts. Only the name and description records differ. | C |
| `tools/verify_fonts.py` on those captures and fonts | Consistency 124/124. Historical 5/5: both 72pt Word Processor screenshots letter-exact (H1), and three 12pt repeat captures identical (H2). | C, G |
| `tests/test_converter.py` (synthetic captures) | 19/19. Includes negative tests: an incomplete file, a clipped glyph, a moved contour, a moved point, a wrong spacing model and a differing repeat capture are all detected. | C |
| `tests/sim/sim_fontcap.py` | 21/21: list-only mode; Cancel; five typefaces including a third-party one with Italic and three sizes, one with no 12pt, one with no sizes; resumed 6–24pt run; "Skip the rest"; uninitialised typeface system; every captured glyph equals the model, none clipped | S |
| `tests/sim/sim_fontdmp4.py`, `sim_fontdmp5.py` | 27/27 and 15/15 | S |

**H2 and blank placeholders.** In run 7, 295 of the blank user-definable placeholders `#B0`–`#CF` differed from run 5. These have no ink and are left out of the fonts. Their metrics lie outside the font's ascender at some sizes, so the empty raster box Rosanne paints for them falls at or beyond the capture rect's edge. FONTDMP4's fixed margins missed or cut it; FONTCAP's larger margins catch more of it. H2 therefore accepts a glyph with **no ink in either capture, identical metrics, and an empty box that is missing or at the rect edge** in one of them. It reports how many it accepted. Every inked glyph must still match exactly.

## 3. FONTCAP.PRG: what is new and what is reused

FONTCAP (`src/fontcap.asm`) reuses, **unchanged**:

* from FONTDMP5: the per-glyph capture (W and K renders, `bios_getpxl` read, record writing), the file, list-reading and alert routines, and the slot survey and guarded `os_typo_init`;
* from FONTDMP4/5: the drawing-area and state-restoring code.

One line differs in the per-glyph code: `os_typo_charinfo` now receives the style with only bit 0 (Bold), as the documentation specifies. For Normal and Bold this is the value FONTDMP4/5 passed.

**New in FONTCAP, and its status after XAnne run 7:**

| Item | Risk if wrong | Status |
|---|---|---|
| Walking every list entry (up to 20) instead of picking Times/Swiss by RTF family | A typeface missed or misread | **R** (run 7, two entries). More than two entries: S only. |
| Size probe: `os_typo_def` / `os_typo_clr` at all ten sizes for every typeface | A size wrongly shown as missing | **R** (all ten found for both). A typeface with fewer sizes: S only. |
| `test_def` treats `A=2` (size not available) as "typeface system ready" | `os_typo_init` called needlessly | S only: Times has 12pt, so the case did not arise |
| Text file output (`FONTLIST.TXT`) and two-line alerts with three buttons | Garbled text or a refused alert | **R** |
| Italic and Bold Italic styles (charscreen IX lo bit 1) | Wrong slant or clipping | S only: no installed typeface lists them |
| Capture rect up to 20 × 144 bytes; asc/desc clamps | Clipping on very large glyphs | **R** for Times/Swiss up to 72pt (nothing clamped or at the edge). Larger glyphs: S only. |
| Plain codes `#20`–`#CF` captured with FONTDMP5's larger margins | None expected: larger rects only | **R**: identical inked glyphs (see H2 above) |

**Not supported, by design:** typefaces beyond the first 20 list entries; accents over bases other than those the documentation allows; synthesising styles a typeface doesn't list.

## 4. Native testing still required

### 4.1 FONTCAP in XAnne: done (run 7, all steps passed)

The procedure is kept here for anyone repeating it on their own installation. Use a **copy** of an XAnne data folder with no `*.FD6` files and no `FONTLIST.TXT`.

1. `sha256sum fontdump/build/FONTCAP.PRG` must match `MANIFEST.md`. Copy it into the folder.
2. **List mode.** Launch FONTCAP and choose **List fonts only**. Photograph every alert. Expected:

   ```
   Font 1 of 2: Times  ID=0100 RTF=1
   Styles 03: Normal Bold.  Sizes: 6 8 10 11 12 14 18 24 36 72
   Font 2 of 2: Swiss  ID=0101 RTF=2
   Styles 01: Normal.  Sizes: 6 8 10 11 12 14 18 24 36 72
   FONTCAP fonts=02 chosen=00 files written=00 skipped(exist)=00 failed=00 no-size=00
   test def=00 init=.. list=C FONTLIST.TXT=W last file=(none)
   ```

   Keep `FONTLIST.TXT`.
3. **Capture, 12pt.** Launch again, choose **Capture fonts**, **Capture** for both typefaces, then **12pt only**. Expect `files written=03` and the files `F0100N12.FD6`, `F0100B12.FD6` and `F0101N12.FD6`, with `FONTLIST.TXT=E`.
4. **Compare with the verified programs.** On Linux, with the FONTDMP4/5 captures of 12pt in another folder:

   ```sh
   python3 tools/fdconvert.py fd6-folder --out fd6-fonts
   python3 tools/verify_fonts.py fd6-folder --fonts fd6-fonts --repeat-run fd4-fd5-folder
   ```

   Every C check must pass. H2 must report every FD4 and FD5 file identical: the same pixels, box and metrics for every code (H2 ignores where a glyph sat in its capture rect, since FONTCAP's margins differ).
5. **Resume.** Delete `F0100B12.FD6`, run step 3 again: expect `files written=01 skipped(exist)=02`.
6. **Optional, all sizes.** Choose **All sizes**: expect `files written=1B` (27 new) and `skipped(exist)=03`. Then run step 4 for all sizes.

### 4.2 Real hardware (wanted)

Steps 1–5 above on a physical PcW16, plus a note of the method used to transfer files and of the time taken. The real-hardware timing and storage limits are unknown (A in `docs/capturing-fonts.md`).

### 4.3 Other typefaces (wanted)

Any PcW16 with typefaces other than Times and Swiss: step 2 (`FONTLIST.TXT`), then a 12pt capture and the verification report. Third-party support should be documented only from such reports.

## 5. Open questions (A)

| # | Question | What would settle it |
|---|---|---|
| A1 | The Word Processor spacing factor (24.175 units/px) is measured from one 72pt line per face. It may depend on the size. | 1:1 WP screenshots of long lines at 12pt and other sizes (`verify_fonts.py --wp-screenshot`) |
| A2 | The TTF line gap reproduces `os_typo_info` line pitch; not compared with WP output | A WP screenshot of several lines |
| A3 | Times Bold spacing not checked against a WP screenshot | A WP screenshot of a Times Bold line |
| A4 | Keystrokes marked `?` in the character tables (`#88`–`#8F`) | Typing them in the Word Processor |
| A5 | The Rosanne-to-Unicode mapping comes from Times and Swiss; other typefaces may differ | A capture of another typeface |
| A6 | All evidence is from XAnne | Section 4.2 |
| A7 | FONTCAP on a typeface other than Times and Swiss, or with Italic styles | Section 4.3 |
