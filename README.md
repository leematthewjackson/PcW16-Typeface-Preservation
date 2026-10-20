# PcW16 Typeface Preservation

**Keep the typefaces of your Amstrad PcW16, exactly as it drew them. (Well as close as!)**

The PcW16 set its documents in its own screen typefaces, each point sized pixel by pixel. This toolkit lets you preserve the typefaces installed on **your own** machine:

1. A small program on the PcW16 has Rosanne draw every character (faster on an emulator than on bare metal).
2. It records exactly what appears on screen. (The PcW16 screen not a modern screen, so we're getting pixel by pixel!)
3. On Linux, those records become bitmap and TrueType fonts you can use today. (With the help of fancy scripts...)

**Here's an example:**

<img width="1461" height="1389" alt="image" src="https://github.com/user-attachments/assets/0f0554ac-8ba1-427a-9421-a28f388a7d08" />


> **Tools, not fonts.** This repository contains no PcW16 fonts, no reconstructed fonts, no captured glyphs and no Rosanne software. You bring your own PcW16, or emulator with your own Rosanne installation, and the tools do the rest.

---

## At a glance

| | |
|---|---|
| **What you run on the PcW16** | `FONTCAP.PRG`: lists your typefaces, lets you choose, captures every character, accent and accented letter |
| **What you run on Linux** | `fdconvert.py`, `verify_fonts.py`, `chartable.py` (Python 3) |
| **What you get** | Pixel-exact fonts for every captured size (BDF and TrueType), installable families such as "PcW16 Times" Regular and Bold, glyph sheets, character tables and a verification report |
| **How faithful** | In testing, every font rebuilt from FONTCAP's captures matched the original screen pixels exactly; letters matched genuine PcW16 Word Processor screenshots |
| **Licence** | GNU GPL v3.0 for the toolkit (see [Licence](#licence)) |

## Why preserve PcW16 typography?

The **Amstrad PcW16** (late-1990s) was a dedicated word-processing computer with its own graphical operating system, **Rosanne**. Its look comes largely from its typefaces. On the installation this toolkit was developed with, those were Times (Normal and Bold) and Swiss (maaa fave), each in ten sizes from 6 to 72 point, and each size is a separately drawn bitmap.

I want to help folks preserve those fonts into the future as the original machines start break down. So the hope with this project is ur not generating a modern look-alike, but **the pixels the PcW16 itself drew**, with its own character widths, line spacing and accented letters. That's what this toolkit records. (Big claims!)

## How it works

```
  PcW16 / XAnne                         Linux
 ┌──────────────────────┐          ┌──────────────────────────────┐
 │ FONTCAP.PRG          │  .FD6    │ fdconvert.py                 │
 │  1 list typefaces    │  files   │  pixels → BDF + TrueType     │
 │  2 you choose        │ ───────► │  family fonts, sheets, data  │
 │  3 Rosanne draws     │          │ verify_fonts.py              │
 │    each character;   │          │  every glyph checked against │
 │    pixels read back  │          │  the capture                 │
 └──────────────────────┘          └──────────────────────────────┘
```

* **Drawing and reading back.** FONTCAP uses only Rosanne's documented programming interface. It draws each character twice, on white and on black, reads the screen back pixel by pixel, and saves the pixels with Rosanne's own metrics. It never opens the font files themselves.
* **Converting.** The Linux tools trace each glyph's pixels into a seam-free outline, and space characters as the PcW16 Word Processor does.
* **Unicode.** Characters are mapped to Unicode, accented letters included (é, č, ő …). (I should have realised this given the Character Map I've used for years!)

The details are in [PROVENANCE.md](PROVENANCE.md).

**About the TrueType files:** they are modern fonts **derived from captured screen pixels**. Each pixel becomes a square in the outline. They are not Amstrad's original outline fonts and don't claim to be.

## Get started

| Stage | | Guide |
|---|---|---|
| **A** | Gather what you need; put `FONTCAP.PRG` on the PcW16 | [Getting started](docs/getting-started.md) |
| **B** | See which typefaces are installed (**List fonts only**) | [Discovering fonts](docs/discovering-fonts.md) |
| **C** | Choose typefaces and sizes; capture | [Capturing fonts](docs/capturing-fonts.md) |
| **D** | Copy the capture files to Linux | [Transferring files](docs/transferring-files.md) |
| **E** | Convert, verify, install, try them out | [Converting on Linux](docs/converting-on-linux.md) |
| **F** | No Linux? Use a virtual machine | [VirtualBox guide](docs/virtualbox-guide.md) |

Something not working? See [Troubleshooting](docs/troubleshooting.md).

**In a hurry?** Once the capture files are on Linux:

```sh
git clone https://github.com/leematthewjackson/PcW16-Typeface-Preservation.git
cd PcW16-Typeface-Preservation
python3 -m venv ~/pcw16-venv && source ~/pcw16-venv/bin/activate
pip install -r fontdump/requirements.txt
python3 fontdump/tools/fdconvert.py ~/pcw16-captures --out ~/pcw16-fonts
python3 fontdump/tools/verify_fonts.py ~/pcw16-captures --fonts ~/pcw16-fonts
```

## What you need

| You need | Why |
|---|---|
| An **Amstrad PcW16** running Rosanne, **or** the **XAnne** emulator with **your own** Rosanne installation | Rosanne draws the characters; the toolkit records what it draws |
| The **typefaces you want to preserve**, installed on it | Nothing is supplied |
| **`FONTCAP.PRG`**, from `fontdump/build/` | The capture program |
| A way to **copy files** between the PcW16 and Linux | Verified for XAnne; not yet for real hardware ([details](docs/transferring-files.md)) |
| **Linux** (or a Linux virtual machine) with **Python 3**, **fontTools** and **Pillow** | The conversion tools |
| **Free space:** about 200 KB per style at 12pt, about 6 MB per style for all sizes | Every pixel of every character is recorded, twice |

## What has been verified

| | Status |
|---|---|
| **FONTCAP.PRG** on Times, Times Bold and Swiss, all ten sizes, in XAnne | **Verified.** It found the typefaces and sizes by itself and resumed correctly. All 33 fonts rebuilt from its captures are identical to the reference set recovered during development. |
| The recovered glyphs against genuine PcW16 Word Processor output | **Verified** at 72pt for Times and Swiss: letter-for-letter identical |
| `FONTDMP4.PRG` and `FONTDMP5.PRG`: the earlier two-step programs for Times, Times Bold and Swiss, included as a fallback | **Verified** in XAnne |
| Other typefaces; Italic and Bold Italic styles; a real PcW16 | **Not yet tested.** Reports are very welcome. |

The evidence and the test plan are in the [technical audit](fontdump/docs/AUDIT.md).

## What's in the box

```
README.md            you are here
PROVENANCE.md        how the process works; what is and isn't included
LICENSE              GNU General Public License v3.0
MANIFEST.md          every file in the package, with checksums
docs/                step-by-step guides (Stages A-F) and troubleshooting
fontdump/
  build/             FONTCAP.PRG, FONTDMP4.PRG, FONTDMP5.PRG: ready to copy to the PcW16
  src/               their Z80 assembly source (Pasmo)
  tools/             fdconvert.py, verify_fonts.py, chartable.py
  tests/             tests on synthetic data, and simulator tests
  docs/              capture file format; technical audit
  build.sh           rebuilds the programs and runs the tests
  requirements.txt   Python libraries
```

Technical reference: [fontdump/README.md](fontdump/README.md) · File format: [fontdump/docs/FORMAT.md](fontdump/docs/FORMAT.md)

## Contributing

Would love to hear from folks doing this on bare metal. What are YOUR experiences. Mine worked, was pretty darned slow compared to an emulator but if you have a machine with an old font you installed and you lost the disk, I am SUPER interested in how it went!

* **Run FONTCAP** in XAnne or on a real PcW16. Send your `FONTLIST.TXT`, photos of the alerts and the verification report.
* **Other typefaces.** If your PcW16 has typefaces beyond Times and Swiss, a `FONTLIST.TXT` and a verification report show whether FONTCAP handles them.
* **Transfer methods** you have actually used to move files from a real PcW16 to a modern computer.
* **Word Processor screenshots** at 1:1 of a line of text in a captured typeface. These let the verifier compare fonts with genuine PcW16 output.

Please don't send capture files or fonts of typefaces you're not entitled to share; the text output is usually enough. (Feel free to rebel I can't stop you!) For code changes:

* keep the existing behaviour unless evidence says otherwise;
* run `fontdump/build.sh --test`;
* describe what you verified and how.

Contributions are accepted under GPL-3.0-only.

Issues and pull requests: https://github.com/leematthewjackson/PcW16-Typeface-Preservation

## Licence

The toolkit (the Z80 programs and their source, the Python tools, the tests and this documentation) is released under the **GNU General Public License, version 3 only** (GPL-3.0-only). See [LICENSE](LICENSE). The `.PRG` programs are built from the source in `fontdump/src/` by `fontdump/build.sh`.

**The licence covers this toolkit only.** It doesn't cover Rosanne, the Amstrad PcW16 software, the original typefaces, or the fonts you reconstruct with it, and the toolkit gives you no rights in those. **You are responsible for establishing your own right to use or distribute any fonts you reconstruct.** [PROVENANCE.md](PROVENANCE.md) records how reconstructed fonts are made, which may help anyone assessing that question.

Amstrad and PcW16 are trademarks of their respective owners. This project is not affiliated with or endorsed by Amstrad or by the owners of the original typefaces. Typeface names such as "Times" may be trademarks: reconstructed fonts are named "PcW16 …" by default, and `--family-prefix` changes that.

**Third-party software, used but not included:**

* Python (PSF licence);
* [fontTools](https://github.com/fonttools/fonttools) (MIT);
* [Pillow](https://python-pillow.org/) (MIT-CMU).

All are compatible with GPL-3.0. Rebuilding the programs needs the [Pasmo](https://pasmo.speccy.org/) assembler, used as a tool only. The optional checks use the OpenType Sanitizer (`opentype-sanitizer`, BSD) and `bdftopcf`.

## Credits

Created by **Lee Matthew Jackson**: [PcW16ers.net](https://pcw16ers.net) · [leematthewjackson.com](https://leematthewjackson.com)

Copyright © 2026 Lee Matthew Jackson. Released under GPL-3.0-only.
