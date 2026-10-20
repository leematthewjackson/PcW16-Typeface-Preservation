# fontdump: the programs and tools

Technical reference. For the step-by-step procedure, start with the [main README](../README.md) and [docs/](../docs/).

## Native programs (Z80, Rosanne)

| Program | Source | What it does | Status |
|---|---|---|---|
| `build/FONTCAP.PRG` | `src/fontcap.asm` | Lists the installed typefaces (`os_typo_getlist`), probes their sizes, writes `FONTLIST.TXT`, lets the user choose typefaces and sizes, and captures every listed style: codes 01–FF and 944 accent combinations, one `.FD6` file per typeface, style and size | Verified in XAnne for Times, Times Bold and Swiss, all sizes. Other typefaces and Italic are untested. See [docs/AUDIT.md](docs/AUDIT.md). |
| `build/FONTDMP4.PRG` | `src/fontdmp4.asm` | Times, Times Bold, Swiss: codes 20–CF, `.FD4` files | Verified in XAnne |
| `build/FONTDMP5.PRG` | `src/fontdmp5.asm` | Times, Times Bold, Swiss: codes 01–1F, D0–FF and the accent combinations, `.FD5` files | Verified in XAnne |

All three are genuine Rosanne `.PRG` applications: a 256-byte zero prefix, loaded at `#4000`, entry at `#4100`, under 16 KB. They:

* use one free typeface slot and clear it again;
* restore the original slot, clip window, ink and mode;
* hide the pointer while drawing;
* confine all drawing to a fixed area of the screen;
* never overwrite a file.

**How a glyph is captured:**

1. `os_typo_charinfo` gives the width, height and baseline height in 1/1800".
2. The capture rectangle is sized from those and from `os_typo_info`, with generous margins.
3. **W render:** the rectangle is cleared white and the glyph drawn opaque with `os_typo_charscreen`. Every pixel is read back with `bios_getpxl`, which gives the ink.
4. **K render:** the same on black. Opaque drawing paints the glyph's raster box white, which shows the box.
5. Both bitmaps and the metrics are written as one `GLY4` record ([docs/FORMAT.md](docs/FORMAT.md)).

## Linux tools (Python 3)

| Tool | Purpose |
|---|---|
| `tools/fdconvert.py` | Captures → BDF, pixel TTF, PNG sheets, glyph PNGs, metadata; installable family fonts. `--help` lists the options. |
| `tools/verify_fonts.py` | Checks the fonts against the captures (C1–C6) and, optionally, against genuine PcW16 output: Word Processor screenshots (H1) and repeat captures (H2) |
| `tools/chartable.py` | Character tables per typeface: picture, Rosanne code, Unicode, PcW16 keystroke, how to type it today |

The tools need Python 3, fontTools and Pillow (`requirements.txt`). Commands: [docs/converting-on-linux.md](../docs/converting-on-linux.md).

**Key conversion rules** (details in the code and in [docs/AUDIT.md](docs/AUDIT.md)):

* **Pixels:** the ink is the black pixels of the W render. The glyph box is the bounding box of the ink plus the K render's white pixels.
* **Outlines:** TrueType outlines trace the union of the ink pixels: outer contours clockwise, holes counter-clockwise, no seams, no curves, no hinting. 64 font units = 1 pixel; 1 em = size × 64 units, so a font built from 12pt is pixel-exact at 12 px.
* **Advances:** by default these follow the PcW16 Word Processor's spacing: the 1/1800" width ÷ 24.175, measured from Word Processor screenshots. `--advance box` uses the raster box width instead.
* **Line gap:** chosen so the line height equals Rosanne's `os_typo_info` line pitch.
* **Underline:** position and thickness are taken from Rosanne's own underscore.
* **Unicode:**
  * Rosanne codes 20–AF are mapped to Unicode as identified from the Times and Swiss glyphs (`ROSANNE_TO_UNICODE`);
  * accent combinations are composed to precomposed Unicode letters, with d/l/t/L plus the apostrophe accent mapped to ď ľ ť Ľ;
  * anything else goes to the Private Use Area;
  * blank, undefined and empty codes are left out.
* **Naming:** fonts are named "PcW16 <name Rosanne reports>" (`--family-prefix`), with the style Rosanne drew. Two typefaces with the same name are told apart by ID.

## Building and testing

```sh
sudo apt install pasmo python3            # Debian/Ubuntu
./build.sh                                # rebuild the three .PRG files, compare with MANIFEST.md
./build.sh --test                         # + tests/test_converter.py (needs fontTools, Pillow)
./build.sh --test /path/to/z80sim-dir     # + the simulator tests, see tests/sim/README.md
```

`build.sh` checks four things for each program: it is at most 16 KB, the 256-byte prefix is zero, `start` is at `#4100`, and the SHA-256 matches `MANIFEST.md`.

| Test | Needs | Covers |
|---|---|---|
| `tests/test_converter.py` | Python, fontTools, Pillow | The converter, verifier and character tables, on synthetic capture files. Includes negative tests. |
| `tests/sim/sim_fontcap.py`, `sim_fontdmp4.py`, `sim_fontdmp5.py` | A Z80 model, `z80sim.py` (not included) | The native programs' logic against a Rosanne mock. An engineering aid only, not evidence of Rosanne's behaviour. |
