# Manifest

Every file in this package. Nothing else belongs in it: no fonts, captures, glyph images, screenshots or PcW16 system files (see `.gitignore` and `PROVENANCE.md`).

## Programs

Built by `fontdump/build.sh` with Pasmo 0.5.3 (`pasmo --bin`). Each loads at `#4000` with a 256-byte zero prefix; `start` is at `#4100`.

| Program | Bytes | SHA-256 | Status |
|---|---|---|---|
| `FONTCAP.PRG` | 14252 | `6b635b9844831249c9c17e6f784606862a3adedf38fbb7009921458bc498e47f` | verified in XAnne run 7 for Times, Times Bold and Swiss, all sizes; other typefaces untested |
| `FONTDMP4.PRG` | 10513 | `2aba651b1c36c411fe678768a8faf3a9a264704fa2fe51c4861cdbe92ddc0f20` | identical to the program verified in XAnne runs 4 and 5 |
| `FONTDMP5.PRG` | 10712 | `0c29074183d6e1a5f01d34fbf3af7ec78050b80c863869aa93546f29491ffb2c` | identical to the program verified in XAnne run 6 |

## All files

Licence: GPL-3.0-only for every file except `LICENSE` itself (the GPL text, (C) Free Software Foundation).

| File | Purpose | SHA-256 |
|---|---|---|
| `.gitignore` | Keeps fonts, captures, images and system files out of the repository | `52ab5099f5dfe833…` |
| `LICENSE` | GNU General Public License v3.0, official text | `3972dc9744f6499f…` |
| `PROVENANCE.md` | How the process works; what is and isn't included | `70145e6e9c50b75b…` |
| `README.md` | Introduction, requirements, overview, licence, contributing | `3634b95e83db26cf…` |
| `docs/capturing-fonts.md` | Stage C: capturing | `ac53b199325d389f…` |
| `docs/converting-on-linux.md` | Stage E: converting, checking, installing | `085019e1640ad5ed…` |
| `docs/discovering-fonts.md` | Stage B: listing the installed typefaces | `1bb0e1e6cdd429d5…` |
| `docs/getting-started.md` | Stage A: preparation | `d35769ffba4211fd…` |
| `docs/transferring-files.md` | Stage D: moving files | `2470cd7d50e264cd…` |
| `docs/troubleshooting.md` | Problems and what to do | `09e8022b014732db…` |
| `docs/virtualbox-guide.md` | Stage F: Linux in VirtualBox for Windows/macOS users | `68a42e4229909765…` |
| `fontdump/README.md` | Technical reference: programs, tools, build, tests | `ea9e72085987a09d…` |
| `fontdump/build.sh` | Builds the .PRG programs, checks them, runs the tests | `afd45deca0e53881…` |
| `fontdump/build/FONTCAP.PRG` | Native program: discover and capture any installed typeface (built from src/fontcap.asm) | `6b635b9844831249…` |
| `fontdump/build/FONTDMP4.PRG` | Native program: Times/Times Bold/Swiss codes 20-CF (built from src/fontdmp4.asm) | `2aba651b1c36c411…` |
| `fontdump/build/FONTDMP5.PRG` | Native program: Times/Times Bold/Swiss accents (built from src/fontdmp5.asm) | `0c29074183d6e1a5…` |
| `fontdump/docs/AUDIT.md` | Technical audit, evidence and verification status, native test plan | `567e4776aff0d1ad…` |
| `fontdump/docs/FORMAT.md` | Capture file formats (versions 4-6) | `542d5b75157c0931…` |
| `fontdump/requirements.txt` | Python libraries for the tools | `5ba3804e331db826…` |
| `fontdump/src/fontcap.asm` | Z80 source of FONTCAP.PRG | `d03bc0954235265b…` |
| `fontdump/src/fontdmp4.asm` | Z80 source of FONTDMP4.PRG | `e2eb112667faad26…` |
| `fontdump/src/fontdmp5.asm` | Z80 source of FONTDMP5.PRG | `c2f0b84a1d417200…` |
| `fontdump/tests/sim/README.md` | How to run the simulator tests | `c8896ad366e20953…` |
| `fontdump/tests/sim/capmodel.py` | FONTCAP extension of the mock: many typefaces, styles, sizes | `9aa07853acead5d4…` |
| `fontdump/tests/sim/rosanne_mock.py` | Rosanne mock for the simulator tests (synthetic glyphs) | `c1ad08b4c4fcee17…` |
| `fontdump/tests/sim/sim_fontcap.py` | Simulator test of FONTCAP.PRG | `287cf42582f88408…` |
| `fontdump/tests/sim/sim_fontdmp4.py` | Simulator test of FONTDMP4.PRG | `c08982d73769e576…` |
| `fontdump/tests/sim/sim_fontdmp5.py` | Simulator test of FONTDMP5.PRG | `38066faf7c819ae7…` |
| `fontdump/tests/test_converter.py` | Tests of the tools on synthetic capture data | `65ffa889d87624a0…` |
| `fontdump/tools/chartable.py` | Character tables per typeface | `b4713e885af9d5eb…` |
| `fontdump/tools/fdconvert.py` | Converter: captures to BDF, TTF, sheets, metadata, family fonts | `0e9fbccff14818af…` |
| `fontdump/tools/verify_fonts.py` | Verifier: fonts against captures and genuine output | `826ffef8bae5f772…` |
| `MANIFEST.md` | This file | |

The source-file checksums change whenever a file is edited; regenerate this table after changes. The program checksums only change when the programs do.
