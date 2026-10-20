# Provenance: how PcW16 Typeface Preservation reconstructs fonts

This document records factually how the toolkit works and what it uses, for anyone assessing rights in fonts made with it. It is not legal advice, and it makes no claim about what may lawfully be distributed in any country.

## Summary

The toolkit does **not** extract, decode or convert the PcW16's font files. It asks the PcW16's own operating system, Rosanne, to draw each character on screen through its documented programming interface. It reads back the pixels Rosanne drew, then rebuilds fonts from those pixels with newly written conversion software.

## What this repository contains

* **Newly written capture programs** (`fontdump/src/*.asm`, built into `fontdump/build/*.PRG`), in Z80 assembly language. They run under Rosanne on a PcW16 or in an emulator. They use only calls described in the Rosanne developer documentation (ROSAN283, "Rosanne d2.75"):
  * `os_typo_getlist` to list the installed typefaces;
  * `os_typo_def`, `os_typo_select` and `os_typo_clr` to install a typeface in a free slot and release it again;
  * `os_typo_info` and `os_typo_charinfo` for the typeface's line pitch and each character's width and height, in 1/1800 inch;
  * `os_typo_charscreen` to draw a character on the screen;
  * the BIOS call `bios_getpxl` to read each screen pixel back;
  * ordinary file, alert, window and pointer calls.
* **Newly written conversion software** (`fontdump/tools/*.py`), in Python. It turns the captured pixels into:
  * **bitmap fonts (BDF):** the pixels themselves;
  * **TrueType fonts (TTF):** each outline is generated mechanically by tracing around the glyph's black pixels, so every outline point lies on a pixel corner. The outlines contain no curves, no hinting instructions, and no code or data tables from any original font.
* **A Rosanne-to-Unicode character mapping** (in `fdconvert.py`), set by this project from the glyphs Rosanne drew.
* **A table of PcW16 keystrokes per character code** (in `chartable.py`), summarised from the Rosanne documentation's keyboard appendix.
* **Short excerpts** from the Rosanne documentation, quoted in source comments to document the programming interface used.
* **Tests that use synthetic data only:** made-up pixel patterns, not PcW16 typefaces.

## What this repository does not contain

* Any Amstrad or Creative Technology program code, operating-system files, ROM or disk images.
* Any PcW16 font file, in its original form or any other.
* Any reconstructed font, captured glyph data, glyph images or screenshots of PcW16 typefaces.
* The Rosanne developer documentation itself.

## What a reconstructed font reproduces

* **Glyph shapes:** the shapes exactly as the PcW16 drew them on its screen, pixel for pixel, at each captured size. They are faithful reproductions, not redesigns: the aim is preservation.
* **Spacing and line pitch:** each character's width and the typeface's line pitch, as Rosanne reports them through `os_typo_charinfo` and `os_typo_info`. These are **numerical data from the original typeface**, reported by the operating system, not measured from the pixels.
* **Names:** the typeface name Rosanne reports, with the prefix "PcW16" by default.

## What the user supplies

The user supplies the PcW16, or an emulator with their own Rosanne installation, and the typefaces installed on it. The capture runs on that installation. Nothing from it is distributed by this project.

## Points relevant to a rights assessment

* **The ownership of the PcW16 typefaces has not been established** by this project. Candidates include Amstrad, Creative Technology (named on the Rosanne documentation), or a type foundry that licensed designs to them. Third-party typefaces installed on a PcW16 may belong to others again.
* **Typeface names may be trademarks**, "Times" in particular. The converter's `--family-prefix` option and the names it writes can be changed.
* **The width and line-pitch figures are data from the original typefaces**, as noted above.
* **Treatment varies by country.** Typeface designs, bitmap fonts and font software are treated differently in different jurisdictions.
* **The GPL licence of this toolkit does not extend to fonts made with it.** People who reconstruct fonts are responsible for establishing their own right to use or distribute them.

## Reproducibility

Every step can be repeated from this repository on a user's own installation:

* `docs/` gives the procedure;
* `fontdump/docs/FORMAT.md` documents the capture files;
* `MANIFEST.md` gives the checksums of the capture programs;
* `fontdump/tools/verify_fonts.py` checks that every generated font holds exactly the captured pixels.
