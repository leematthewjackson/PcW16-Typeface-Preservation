#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Lee Matthew Jackson - PcW16ers.net & leematthewjackson.com
#
# Reproducible build of the PcW16 Typeface Preservation programs.
#   FONTCAP.PRG   (src/fontcap.asm)   discover and capture any installed typeface
#   FONTDMP4.PRG  (src/fontdmp4.asm)  Times/Times Bold/Swiss, codes 20-CF (XAnne-verified)
#   FONTDMP5.PRG  (src/fontdmp5.asm)  Times/Times Bold/Swiss, accents (XAnne-verified)
# Needs: pasmo (Debian/Ubuntu: sudo apt install pasmo), sha256sum.
#
#   ./build.sh                     build into build/, check, compare with MANIFEST.md
#   ./build.sh --test              also run tests/test_converter.py (Python, synthetic data)
#   ./build.sh --test Z80SIM_DIR   also run the simulator tests (tests/sim/README.md)
set -eu
cd "$(dirname "$0")"
mkdir -p build
status=0
for pair in fontcap:FONTCAP fontdmp4:FONTDMP4 fontdmp5:FONTDMP5; do
  src=${pair%%:*}; prg=${pair##*:}
  pasmo --bin "src/$src.asm" "build/$prg.PRG" "build/$src.sym"
  size=$(wc -c < "build/$prg.PRG")
  [ "$size" -le 16384 ] || { echo "$prg.PRG is $size bytes: exceeds the 16K loader block" >&2; exit 1; }
  # .PRG convention: 256-byte zero prefix, entry at #4100 (ROSAN283 'Memory Layout')
  head -c 256 "build/$prg.PRG" | od -An -tx1 | tr -d ' \n' | grep -qv '[1-9a-f]' \
    || { echo "$prg: zero prefix check failed" >&2; exit 1; }
  grep -q '^start[[:space:]]*EQU 04100H' "build/$src.sym" || { echo "$prg: start is not at #4100" >&2; exit 1; }
  rm -f "build/$src.sym"
  sum=$(sha256sum "build/$prg.PRG" | cut -d' ' -f1)
  if grep -q "$sum" ../MANIFEST.md; then match="matches MANIFEST.md"; else match="DIFFERS from MANIFEST.md"; status=1; fi
  echo "$prg.PRG $size bytes sha256 $sum ($match)"
done
if [ "${1:-}" = "--test" ]; then
  python3 tests/test_converter.py
  if [ -n "${2:-}" ]; then
    python3 tests/sim/sim_fontcap.py "$2" build/FONTCAP.PRG
    python3 tests/sim/sim_fontdmp4.py "$2" build/FONTDMP4.PRG
    python3 tests/sim/sim_fontdmp5.py "$2" build/FONTDMP5.PRG
  fi
fi
exit $status
