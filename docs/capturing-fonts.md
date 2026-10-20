# Stage C: Capture your fonts

## C1. Run a capture

1. Make sure there is enough free space: see [getting-started.md](getting-started.md#a2-how-much-space-and-time).
2. In the PcW16 **File Manager**, launch `FONTCAP.PRG`.
3. At the first alert choose **Capture fonts**.
4. FONTCAP writes `FONTLIST.TXT` (unless it already exists), then shows **one alert per installed typeface** with its styles and sizes ([discovering-fonts.md](discovering-fonts.md#b2-read-the-list)). For each one choose:
   * **Capture**: preserve this typeface, in every style it has;
   * **Skip**: not this one;
   * **Skip the rest**: no more typefaces; capture the ones chosen so far.

   A typeface with no usable size shows **OK** only and can't be chosen.
5. Then choose the sizes:
   * **12pt only**: quick and small. Good for a first test.
   * **6pt to 24pt**: the text sizes, 8 sizes.
   * **All sizes**: 6pt to 72pt, 10 sizes. The 36pt and 72pt files are large.
6. FONTCAP draws each character in a box on the screen, first on white, then on black. You'll see characters and accented letters flash past. The pointer is hidden while it works. **Leave the machine alone until the summary alerts appear.**

## C2. What it captures

For each chosen typeface, each chosen size that the typeface has, and **every style the typeface lists** (Normal, Bold, Italic, Bold Italic):

* every single character code from 01 to FF. Codes the typeface doesn't define are noted, but nothing is drawn for them;
* every accent (D0–DF) over every letter Rosanne allows accents on: space, A–Z, a–z, Æ æ Œ œ and Ø ø. That's 944 combinations, drawn by Rosanne exactly as it composes them;
* the typeface's line pitch and ascender/descender, and every character's width and height, as Rosanne reports them.

## C3. The files it writes

One file per typeface, style and size:

```
F0100N12.FD6
│└┬─┘│└┤
│ │  │ └─ size in points (2 digits: 06 ... 72)
│ │  └─── style: N Normal, B Bold, I Italic, J Bold Italic
│ └────── Rosanne's typeface ID (4 hex digits, as in FONTLIST.TXT)
└──────── F for FONTCAP
```

For example, with Times (ID 0100) and Swiss (ID 0101) at 12pt: `F0100N12.FD6`, `F0100B12.FD6`, `F0101N12.FD6`. The format is documented in [`fontdump/docs/FORMAT.md`](../fontdump/docs/FORMAT.md).

## C4. Recognising success

Two summary alerts appear at the end (numbers in hexadecimal):

```
FONTCAP fonts=02 chosen=02 files written=03 skipped(exist)=00 failed=00 no-size=00
test def=00 init=FF list=C FONTLIST.TXT=W last file=F0101N12
```

* `files written`: files completed in this run.
* `skipped(exist)`: files that already existed and were left alone (see C6).
* `failed`: should be `00`. Otherwise a third alert names the last failure (see C5).
* `no-size`: chosen typefaces that lack a chosen size. That's normal for a typeface with fewer sizes.

**Success means `failed=00` and the expected number of files.** Final confirmation comes on Linux: the converter reports any file that is incomplete or any character that may have been cut off ([converting-on-linux.md](converting-on-linux.md)).

## C5. If something goes wrong

| What happens | What it means | What to do |
|---|---|---|
| `failed=01` (or more) and an alert `last failure F0100N72 W=xx` | **W** = writing failed, usually because the disk is full. **O** = the file could not be created. **D** = Rosanne refused to install the typeface at that size (`xx` is its error code). | Free some space or use another disk/folder. **Delete the failed file** (it's incomplete), then run FONTCAP again with the same choices. Finished files are skipped. |
| `FONTCAP: no free typo slot (0-15): nothing done` | All 16 typeface slots are in use by other programs | Close other applications, or restart the PcW16, and try again. Nothing was changed. |
| `list=-`, `fonts=00` | Rosanne returned no readable typeface list | See [troubleshooting.md](troubleshooting.md). |
| The machine is switched off, crashes or is reset during a capture | The file being written lacks its end marker | Run FONTCAP again with the same choices. Finished files are skipped. Before converting, delete the incomplete file: the converter names it ("INCOMPLETE"). |

## C6. Resuming and adding more later

FONTCAP **never overwrites a file**. If a capture file already exists it is skipped and counted under `skipped(exist)`. So:

* **To resume an interrupted run:** delete the incomplete file, if you know which it is, then run FONTCAP with the same choices. If you're not sure, convert on Linux first; the converter lists incomplete files.
* **To add sizes or typefaces later:** run FONTCAP again and choose them. Existing files are left alone.
* **To redo a file:** delete it first.

On the PcW16 itself there is no way to stop FONTCAP once capturing has started, apart from switching off; C5 explains how to recover from that.

## C7. Limitations of the current version

* **Verified so far:** FONTCAP is verified in XAnne for Times, Times Bold and Swiss at all sizes. **Other typefaces, Italic and Bold Italic styles, and real hardware have not been tested yet.** Run the verification in Stage E on everything you capture, and please report results. Status: [`fontdump/docs/AUDIT.md`](../fontdump/docs/AUDIT.md).
* **At most 20 typefaces** in Rosanne's list are handled. `FONTLIST.TXT` reports how many Rosanne listed.
* **Character set:** characters are captured by Rosanne code (01–FF), and accents only over the letters Rosanne's documentation allows. The conversion to Unicode was worked out from Times and Swiss. A third-party typeface with a different character layout would need its own mapping (or `--raw-encoding`).
* **Very large glyphs:** each character is captured in a box of at most 160 × 144 pixels, with at most 136 rows above the baseline and 56 below. Times and Swiss at 72pt fit with room to spare. If a character of another typeface doesn't fit, the converter reports it as possibly clipped; please report it.
* **Only what is on screen:** FONTCAP records the screen fonts. Printed output may have used different data.

## Using the older programs instead

`FONTDMP4.PRG` (plain characters 20–CF) and `FONTDMP5.PRG` (accents, accented letters and the remaining codes) are the XAnne-verified programs for **Times, Times Bold and Swiss only**. They show a size menu (**12pt only** / **All sizes** / **Cancel**) and write `FD4TN012.FD4`-style and `FD5TN012.FD5`-style files (TN Times Normal, TB Times Bold, SN Swiss Normal). Run both to get the full character set; the converter merges them. They also skip existing files.

Next: [Stage D, transfer the files](transferring-files.md).
