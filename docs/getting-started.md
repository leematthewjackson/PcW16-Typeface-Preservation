# Stage A: Preparation

This guide gets everything ready. You need no programming knowledge: the steps are copying files, launching a program and typing commands that are given in full.

## A1. What you need, and what each part does

| Part | What it is | Why it is needed |
|---|---|---|
| **A PcW16 running Rosanne**, or the **XAnne** emulator with your own Rosanne installation | The machine whose typefaces you want to keep | Rosanne draws every character on screen. The toolkit records exactly what it draws, so the original software must be running. |
| **The fonts you want to preserve**, installed on that machine | Usually Times and Swiss; possibly others | The toolkit captures what is installed. It supplies no fonts. |
| **`FONTCAP.PRG`** | A small native PcW16 program from this repository, in `fontdump/build/` | It lists your installed typefaces, lets you choose, draws every character and saves the pixels and metrics. |
| **A way to move files between the PcW16 and a Linux computer** | Depends on your setup | `FONTCAP.PRG` has to get onto the PcW16, and the capture files have to come back. See [transferring-files.md](transferring-files.md). |
| **A Linux computer** (a real one, or a virtual machine) | Any recent distribution, for example Ubuntu or Debian | The conversion tools are written for Linux. Windows and macOS users can run Linux in a virtual machine: [virtualbox-guide.md](virtualbox-guide.md). |
| **Python 3** with **fontTools** and **Pillow** | Free software, installed in Stage E | Python runs the conversion; fontTools writes TrueType fonts; Pillow writes the glyph images. |
| **Free space** | On the PcW16 (or in XAnne's folder) and on Linux | See A2. |

## A2. How much space and time

Capture files hold every pixel of every character, twice: once drawn on white and once on black. The figures below were measured with FONTCAP in XAnne on the standard Times and Swiss typefaces. Other typefaces may differ.

| What you capture | Capture files | Time in XAnne at 500 % speed |
|---|---|---|
| One style of one typeface, **12pt only** | about 200 KB | about 18 s |
| One style, **6pt to 24pt** (8 sizes) | about 1.8 MB | about 3 minutes |
| One style, **all sizes** (6pt to 72pt) | about 5.3–5.9 MB | about 8–9 minutes |
| The 72pt size alone | about 2.8–3.1 MB | about 4–5 minutes |
| Times, Times Bold and Swiss, all sizes (30 files) | about 17 MB | about 25 minutes |

The times come from the emulator's own clock and are only a guide. **On a real PcW16 the times have not been measured yet**, and storage space may be the limit. A single 72pt capture file is larger than a 1.44 MB floppy disk. Choose **12pt only** or **6pt to 24pt** if space is short; you can capture other sizes in a later run (see [capturing-fonts.md](capturing-fonts.md)).

On Linux, the fonts and images generated from one style at all sizes take about 10–20 MB.

## A3. Get the toolkit

On your Linux computer:

```sh
git clone https://github.com/leematthewjackson/PcW16-Typeface-Preservation.git
cd PcW16-Typeface-Preservation
```

Or download the repository as a ZIP from its GitHub page and unpack it.

The ready-made programs are in `fontdump/build/`:

| File | Use |
|---|---|
| `FONTCAP.PRG` | **The one to use.** Lists, chooses and captures any installed typeface. |
| `FONTDMP4.PRG`, `FONTDMP5.PRG` | Earlier programs for Times, Times Bold and Swiss only (plain characters, then accents). XAnne-verified; kept as a fallback. |

Check that the files are intact. The expected checksums are in [`MANIFEST.md`](../MANIFEST.md):

```sh
sha256sum fontdump/build/*.PRG
```

To rebuild the programs from source instead, see [`fontdump/README.md`](../fontdump/README.md).

## A4. Put FONTCAP.PRG on the PcW16

* **XAnne:** XAnne keeps the PcW16's folders as ordinary folders on your computer. Copy `FONTCAP.PRG` into the folder that appears in the PcW16 File Manager, for example a folder named like `FOLDER01`. Where these folders are depends on your XAnne setup. See [transferring-files.md](transferring-files.md).
* **Real PcW16:** a verified method has not yet been documented by this project. See [transferring-files.md](transferring-files.md).

**Use a copy of your setup.** FONTCAP only ever creates new files and never overwrites one. Even so, when you're working with irreplaceable data, start from a backup. In XAnne, copy the whole data folder first.

Next: [Stage B, discover your fonts](discovering-fonts.md).
