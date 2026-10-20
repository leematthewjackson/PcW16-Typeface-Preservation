# Simulator tests

These tests run the `.PRG` programs on a Z80 CPU model against a mock of the Rosanne calls they use (`rosanne_mock.py`, `capmodel.py`). The mock draws **synthetic** patterns, not PcW16 typefaces.

They are an **engineering aid only**. A pass means the program does what the test expects on this model of the CPU and of Rosanne. It is not evidence of how Rosanne behaves: only runs in XAnne or on a real PcW16 are (`../../docs/AUDIT.md`).

**The Z80 model, `z80sim.py`, is not included in this repository.** The tests were run with the project's own Z80 model, which is part of a separate project. The tests expect a module `z80sim` providing:

* `CPU(image)`, with registers as attributes (`a`, `f`, `b` … `l`, `bc`, `de`, `hl`, `ix`, `pc`, `steps`) and memory `mem`;
* `step()`, which runs one instruction;
* `_call(target)`, the hook for `call` instructions;
* `_alert_text()` and `_alert_buttons()`, which decode an `os_alert` definition;
* `_push16()`;
* the exceptions `SimError`, `SimRunaway` and `_SimStop`.

```sh
python3 sim_fontcap.py  /path/to/z80sim-dir ../../build/FONTCAP.PRG
python3 sim_fontdmp4.py /path/to/z80sim-dir ../../build/FONTDMP4.PRG
python3 sim_fontdmp5.py /path/to/z80sim-dir ../../build/FONTDMP5.PRG   # after sim_fontdmp4.py
```

The FONTDMP tests write their simulated capture files to `../../build/sim-sample/`.
