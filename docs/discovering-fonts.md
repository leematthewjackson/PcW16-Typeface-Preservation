# Stage B: Discover your installed fonts

FONTCAP can list every typeface Rosanne reports as installed, without capturing anything. This is quick and safe, and it tells you what you can preserve.

## B1. Run FONTCAP in list mode

1. In the PcW16 **File Manager**, open the folder holding `FONTCAP.PRG` and launch it like any other program.
2. The first alert says *"FONTCAP: preserve the typefaces installed on this PcW16."* Choose **List fonts only**.
3. One alert appears for each installed typeface. Press **OK** after each. Taking a photo of each alert is useful if you want to report results.
4. Two summary alerts follow (see B3).
5. FONTCAP has written **`FONTLIST.TXT`** in the same folder.

Nothing else is changed. FONTCAP installs each typeface briefly in a free typeface slot to find its sizes, then clears the slot again. If `FONTLIST.TXT` already exists, FONTCAP leaves it alone and writes nothing. Delete or rename the old one first if you want a fresh list.

## B2. Read the list

Each alert, and each line of `FONTLIST.TXT`, looks like this:

```
Font 1 of 2: Times  ID=0100 RTF=1 | Styles 03: Normal Bold.  Sizes: 6 8 10 11 12 14 18 24 36 72
```

| Part | Meaning |
|---|---|
| `Font 1 of 2` | Position in Rosanne's typeface list |
| `Times` | The name Rosanne reports. The fonts you make are called "PcW16 Times" by default. |
| `ID=0100` | Rosanne's 16-bit typeface identifier, in hex. It goes into the capture file names, so two typefaces never collide. |
| `RTF=1` | The RTF family Rosanne reports: 0 = unknown, 1 = Times (serif), 2 = Swiss (sans serif). |
| `Styles 03: Normal Bold` | The styles the typeface has. The number is a bitmask: 1 = Normal, 2 = Bold, 4 = Italic, 8 = Bold Italic. FONTCAP captures every style listed. |
| `Sizes: 6 8 …` | The point sizes Rosanne accepts for this typeface. FONTCAP tries every size Rosanne supports (6, 8, 10, 11, 12, 14, 18, 24, 36 and 72) and lists those that work. |
| `(def error xx)` | Only if a size failed for a reason other than "size not available". Report it (see [troubleshooting.md](troubleshooting.md)). |
| `Sizes: none` | Rosanne would not install this typeface at any size, so FONTCAP can't capture it. |

The list on the installation this toolkit was developed with:

```
Font 1 of 2: Times  ID=0100 RTF=1 | Styles 03: Normal Bold.  Sizes: 6 8 10 11 12 14 18 24 36 72
Font 2 of 2: Swiss  ID=0101 RTF=2 | Styles 01: Normal.  Sizes: 6 8 10 11 12 14 18 24 36 72
```

That list is exactly what FONTCAP showed and wrote in XAnne.

**Styles are part of one typeface.** On this installation, Times Bold isn't a separate entry: it is the Bold style of Times. Swiss has no Bold style, and FONTCAP won't invent one.

## B3. The summary alerts

```
FONTCAP fonts=02 chosen=00 files written=00 skipped(exist)=00 failed=00 no-size=00
test def=00 init=FF list=C FONTLIST.TXT=W last file=(none)
```

Numbers are in hexadecimal.

| Field | Meaning |
|---|---|
| `fonts` | Valid entries in Rosanne's list |
| `test def` | 00: Rosanne answered the first test definition normally |
| `init` | `FF`: FONTCAP didn't need to initialise the typeface system. Any other value: it did, because the list wasn't ready, which happens under File Manager on a freshly started system. That is normal. |
| `list` | `C` or `M`: how the list was read (two methods). `-`: no valid list was found, so see [troubleshooting.md](troubleshooting.md). |
| `FONTLIST.TXT` | `W` written, `E` already existed and left alone, `F` writing failed (disk full?) |

Next: [Stage C, capture](capturing-fonts.md).
