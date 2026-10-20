# Stage E: Convert the captures on Linux

Every command below can be copied and pasted into a terminal. Lines starting with `#` are comments. The examples assume:

* the toolkit is in `~/PcW16-Typeface-Preservation`;
* your capture files are in `~/pcw16-captures` (Stage D);
* the fonts will be written to `~/pcw16-fonts`.

Change these paths if yours differ.

## E1. Install Python 3 and the required libraries

Debian, Ubuntu, Linux Mint, Raspberry Pi OS:

```sh
sudo apt update
sudo apt install python3 python3-venv git
```

Fedora:

```sh
sudo dnf install python3 git
```

Then create a **virtual environment**: a private folder for the two libraries, so nothing is installed system-wide. Then install them:

```sh
cd ~/PcW16-Typeface-Preservation
python3 -m venv ~/pcw16-venv
source ~/pcw16-venv/bin/activate
pip install -r fontdump/requirements.txt
```

`fontdump/requirements.txt` lists **fontTools** (writes the TrueType fonts) and **Pillow** (writes the glyph images). `opentype-sanitizer` is optional: it adds one validity check, the one web browsers use.

In every new terminal, run `source ~/pcw16-venv/bin/activate` again before the commands below. The prompt then starts with `(pcw16-venv)`.

## E2. Convert

```sh
cd ~/PcW16-Typeface-Preservation
python3 fontdump/tools/fdconvert.py ~/pcw16-captures --out ~/pcw16-fonts
```

You can list several folders or individual files. The converter groups the files by typeface, style and size from their contents, not their names. Files from the older programs (`.FD4` with `.FD5`) are merged automatically.

The output looks like this, one block per typeface, style and size:

```
F0100N12.FD6: Times Regular 12pt id=0100 drawn=1104 in font=1104 undefined=95 time~18s complete=True
family font: /home/you/pcw16-fonts/family/PcW16Times-Regular.ttf
```

**Watch for lines starting with `PROBLEM:`.** The converter ends with exit status 1 if any appear:

| Problem | Meaning | What to do |
|---|---|---|
| `INCOMPLETE file (no END record)` | The capture was interrupted or the copy is incomplete | Delete it on the PcW16 and capture it again ([capturing-fonts.md](capturing-fonts.md#c6-resuming-and-adding-more-later)) |
| `box touches the capture edge (may be clipped): …` | A character may extend past its capture box | Please report it, with the typeface and the codes listed |
| `capture rect clamped: …` | A character was too large for the capture box | As above |

## E3. What you get

```
~/pcw16-fonts/
  Times-Regular-12pt/
    PcW16-Times-Regular-12.ttf    size-specific TrueType font: pixel-exact at 12 px
    PcW16-Times-Regular-12.bdf    size-specific bitmap font: the pixels themselves
    sheet.png                     every character, enlarged, with its Rosanne code
    sheet-accents.png             every accented letter
    glyphs/                       one PNG per character, 1:1
    metadata.json                 every metric Rosanne reported, per character
  Times-Bold-12pt/ ...            one folder per typeface, style and size
  family/
    PcW16Times-Regular.ttf        installable family fonts: "PcW16 Times" Regular,
    PcW16Times-Bold.ttf           Bold, ... built from one size (default 12pt)
  rosanne-to-unicode.json         the character mapping used
```

**Two kinds of font, for two purposes:**

* **Size-specific fonts** (`<Name>-<Style>-<size>pt/`): one per captured size, because each size is a separately designed bitmap. Use these to reproduce the original appearance at that size.
* **Family fonts** (`family/`): one font per style, all with the family name "PcW16 <Name>", built from one size. They are **scalable TrueType fonts derived from captured pixels**, not original outline fonts. Scaled up they show the pixels of that one size, enlarged.

Only the styles Rosanne reported are produced: nothing is synthesised. A Bold or Italic that your word processor shows for a typeface that lacks it is your software's imitation.

**Options:**

| Option | Effect |
|---|---|
| `--family-master 14` | Build the family fonts from 14pt instead of 12pt. Different sizes give noticeably different looks. |
| `--family-sizes 10,14,18` | Also build complete family sets from those sizes, in `family/10pt/` etc., with the same names, to compare. Install only one set per typeface at a time. |
| `--family-prefix MyPrefix` | Name the fonts "MyPrefix Times" etc. instead of "PcW16 Times" |
| `--advance box` | Space characters by their pixel boxes instead of the Word Processor's spacing |
| `--raw-encoding` | Keep Rosanne's own character codes instead of Unicode |

## E4. Check the results

```sh
python3 fontdump/tools/verify_fonts.py ~/pcw16-captures --fonts ~/pcw16-fonts | tee ~/pcw16-fonts/verify-report.txt
```

It checks every generated font against the captures and prints `PASS` or `FAIL` for each:

* C1: the capture is complete and unclipped;
* C2: every TrueType outline, rasterised, equals the captured pixels;
* C3: every BDF bitmap equals the capture;
* C4: each character is mapped once;
* C5: the family fonts equal their master size;
* C6: the fonts pass the OpenType Sanitizer.

The last lines summarise:

```
consistency: 21/21 passed
historical: 0/0 passed
```

Run it with the same `--family-master` and `--family-prefix` options you used for the conversion.

**Optional, comparison with genuine PcW16 output:** take a screenshot at 1:1 of one line of black text in the PcW16 Word Processor, in a captured typeface and size, for example 72pt Times "This is a test". Crop it to the text and pass it as `NAME-STYLE:SIZE:TEXT:FILE`:

```sh
python3 fontdump/tools/verify_fonts.py ~/pcw16-captures --fonts ~/pcw16-fonts \
    --wp-screenshot "Times-Regular:72:This is a test:wp-times-72.png"
```

H1 passes when every letter in the screenshot has exactly the captured pixels, at the Word Processor's spacing.

**Look at the sheets** too. Open `sheet.png` and `sheet-accents.png` in any image viewer: `xdg-open ~/pcw16-fonts/Times-Regular-12pt/sheet.png`. Characters marked `!` touch their capture edge.

**Character tables:** `python3 fontdump/tools/chartable.py ~/pcw16-fonts` writes `family/Characters-<font>.md`. Each table lists every character with its picture, Unicode name, PcW16 keystroke and how to type it today.

## E5. Install the fonts on your computer

```sh
mkdir -p ~/.local/share/fonts/pcw16
cp ~/pcw16-fonts/family/*.ttf ~/.local/share/fonts/pcw16/
fc-cache -f
fc-list | grep -i pcw16
```

The last command should list your fonts, for example `PcW16 Times:style=Bold`. To remove them: `rm -r ~/.local/share/fonts/pcw16 && fc-cache -f`.

## E6. Try them in an ordinary application

1. Open LibreOffice Writer (or any word processor) and type some text, including accented letters such as `façade naïve ďábel`.
2. Choose the font "PcW16 Times" (or your typeface) from the font list. Make a line bold to check the Bold style, if your typeface has one.
3. **For a pixel-exact look**, the text must be drawn with one font pixel per screen pixel: the font's **pixel size** must equal the captured point size. At 100% zoom on a typical 96 dpi screen, 1 point is 1.33 pixels, so a font built from 12pt is pixel-exact at **9pt** (12 px), and one built from 14pt at **10.5pt** (14 px). Alternatively keep 12pt text and set the zoom to 75%. At other sizes the fonts still work, just slightly less crisply.

Characters Rosanne could compose but Unicode has no single character for (for example B with a grave accent) are in the Private Use Area. Insert them with a character map application; the character tables list their code points.

## E7. Bitmap (BDF) fonts

The BDF files can be compiled for X11 bitmap-font applications:

```sh
sudo apt install xfonts-utils        # provides bdftopcf
bdftopcf -o times12.pcf ~/pcw16-fonts/Times-Regular-12pt/PcW16-Times-Regular-12.bdf
```

Most modern applications use the TrueType fonts instead.
