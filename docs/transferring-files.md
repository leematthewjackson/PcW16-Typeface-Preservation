# Stage D: Transfer the files to Linux

You need to move two kinds of file:

* **to the PcW16:** `FONTCAP.PRG` (Stage A);
* **from the PcW16:** the capture files (`*.FD6`, or `*.FD4` and `*.FD5` from the older programs) and `FONTLIST.TXT`.

Capture files are binary. Copy them unchanged: no text conversion, no renaming.

## XAnne (verified)

XAnne keeps the PcW16's folders as **ordinary folders on the computer it runs on**. A program copied into such a folder appears in the PcW16 File Manager. Files the PcW16 writes there appear on the host computer straight away. The captures used to develop this toolkit were moved this way: the program was copied into the emulated PcW16's folder, and the capture files were copied out of it afterwards.

Where the folders are depends on how XAnne is set up on your computer: look for a folder named like `FOLDER01` holding your PcW16 documents. On Linux, for example:

```sh
# find the folder (adjust the starting point if needed)
find ~ -maxdepth 6 -type d -name 'FOLDER0*' 2>/dev/null

D=/path/to/your/FOLDER01                       # the folder you found
cp -n fontdump/build/FONTCAP.PRG "$D"/         # -n: never overwrite an existing file
```

After the capture:

```sh
mkdir -p ~/pcw16-captures
cp -n "$D"/*.FD6 "$D"/FONTLIST.TXT ~/pcw16-captures/
ls -l ~/pcw16-captures
```

If XAnne runs on Windows or macOS, copy the same files with that system's file manager into a folder you share with your Linux virtual machine ([virtualbox-guide.md](virtualbox-guide.md)), or pack them into a ZIP or `.tar.gz` file and unpack it on Linux.

**Make a backup copy of the capture files before converting.** They are your original record. The converter only reads them, but a second copy costs nothing.

## A real PcW16 (not yet verified)

**This project has not yet verified a way to move files between a real PcW16 and a modern computer**, so none is described here as working. Points to keep in mind:

* The capture files can be large. A 72pt file is about 2.8–3.1 MB, more than a 1.44 MB floppy disk holds. Capture a few sizes at a time (Stage C: **12pt only** or **6pt to 24pt**), move them off, and continue later: existing files are skipped.
* Check that each file arrives at **exactly its original size**, and compare checksums where you can. The converter detects files that are cut short, but not other damage.
* If you find a method that works, please report it (see the main [README](../README.md#contributing)), with the PcW16 model and Rosanne version, the method and the disk format. It will be added here once confirmed.

Next: [Stage E, convert on Linux](converting-on-linux.md).
