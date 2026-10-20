# Troubleshooting

## On the PcW16

| Symptom | Likely cause | What to do |
|---|---|---|
| `FONTCAP.PRG` doesn't appear in File Manager | It's not in the folder File Manager is showing | Check the folder; in XAnne, check that you copied it into the folder the emulated PcW16 uses ([transferring-files.md](transferring-files.md)) |
| `FONTCAP: no free typo slot (0-15): nothing done` | All 16 typeface slots are in use | Close other applications or restart the PcW16, then try again. Nothing was changed. |
| `fonts=00`, `list=-` in the summary | Rosanne returned no readable typeface list, even after FONTCAP initialised the typeface system | Restart the PcW16 and launch FONTCAP from File Manager before any other program. If it persists, report the summary alerts. |
| `init=` is not `FF` | FONTCAP had to initialise the typeface system first, because the list wasn't ready | Normal under File Manager on a freshly started system |
| `test def=` is not `00` or `02` | Rosanne refused to install the first typeface | Report the alerts. `01` means "font does not exist", `07` not enough memory, `08` slot occupied. |
| A typeface shows `Sizes: none` | Rosanne wouldn't install it at any size. `(def error xx)` gives the reason. | Report your `FONTLIST.TXT` |
| `failed=` is not `00`, last failure `… W=xx` | Writing the file failed, usually a full disk | Free space, delete the named (incomplete) file, run FONTCAP again with the same choices |
| last failure `… O=xx` | The file couldn't be created | Check the disk isn't write-protected or full |
| last failure `… D=xx` | Rosanne refused that typeface and size (`xx` as for `test def`) | Report it |
| `FONTLIST.TXT=E` | `FONTLIST.TXT` already existed; FONTCAP never overwrites files | Delete or rename the old file for a fresh list |
| `skipped(exist)` is larger than expected | Files from an earlier run exist and were left alone | Delete the files you want captured again |
| `no-size` is not `00` | A chosen typeface lacks a chosen size | Normal for a typeface with fewer sizes |
| The machine was switched off or crashed during a capture | The file being written is incomplete | Run FONTCAP again with the same choices; delete the incomplete file first if you know which it is. The converter will name it. |

## On Linux

| Symptom | What to do |
|---|---|
| `python3: command not found` | Install Python 3: [converting-on-linux.md](converting-on-linux.md#e1-install-python-3-and-the-required-libraries) |
| `ModuleNotFoundError: No module named 'fontTools'` (or `PIL`) | Activate the virtual environment: `source ~/pcw16-venv/bin/activate`, then `pip install -r fontdump/requirements.txt` |
| `error: externally-managed-environment` from pip | You're not in the virtual environment. Activate it, as above. |
| `no .FD4 / .FD5 / .FD6 capture files found` | Check the folder you gave the converter. The file extensions must be kept. |
| `not a capture file` | The file is damaged or isn't a capture file. Copy it again from the PcW16, unchanged. |
| `PROBLEM: INCOMPLETE file` | The capture was interrupted, or the copy is incomplete. Compare the file size with the original; capture it again if needed. |
| `PROBLEM: box touches the capture edge` | A character may be cut off. Report the typeface, size and the codes listed. |
| `note: no 12pt capture of …: no family font` | The family fonts are built from 12pt by default. Capture 12pt, or choose a captured size with `--family-master`. |
| A `FAIL` line from `verify_fonts.py` | Make sure you used the same `--family-master` and `--family-prefix` for both commands. Convert again into an empty folder. If it persists, report the full output. |
| Fonts don't appear in applications | Run `fc-cache -f` and restart the application; check with `fc-list \| grep -i pcw16` |
| Text looks slightly blurry or uneven | Use a pixel-exact size and zoom: [converting-on-linux.md](converting-on-linux.md#e6-try-them-in-an-ordinary-application) |
| Two very similar fonts in the font menu | An earlier set, or a per-size font, is installed as well. Remove one: [converting-on-linux.md](converting-on-linux.md#e5-install-the-fonts-on-your-computer) |

## Reporting a problem

Please include:

* `FONTLIST.TXT`;
* photos or transcripts of the alerts;
* the converter's output and `verify-report.txt`;
* the PcW16 model and Rosanne version, or XAnne version;
* what you did.

Please don't send capture files or fonts of typefaces you're not entitled to share. The text output is usually enough.
