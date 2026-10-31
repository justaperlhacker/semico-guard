# Contributing — report a wedge, help close the loop

The SEMICO-wedge ledger grows more useful with every unit that reports in.

## Reporting your own wedge

1. **Install the guard** (README.md → Install), even if it "only" protects.
   It journals the wedge frames with timestamps and transport attribution.
2. **Grab your report data**:
   ```
   sudo journalctl -u semico-guard --since today --no-pager > /tmp/semico-guard.log
   lsusb
   uname -a
   ```
3. **Open an issue** on this repository with:
   * your full model string from `lsusb` (e.g. `1a2c:7504`, or your 2.4G/BT PID),
   * keyboard product name (e.g. K552-KRS, K600, …) and firmware/app versions
     (the KUMARA app shows the firmware it *thinks* you have),
   * which mode it wedged in (wired / 2.4G / BT),
   * whether you were *typing* or the keyboard was sitting **idle** (both matter!),
   * omit nothing: attach `/tmp/semico-guard.log` if it contains wedge frames.
4. If you captured raw frames yourself (`tooling/kbd-capture.py` or manual
   hidraw taps), include the exact hex lines — those are the gold standard
   for reproducing the byte signature across *any* sister board.

## If you want to help with code

* `resetv2/` — the over-the-air factory reset experiment: read the plan,
  capture your own vendor-command bytes, and share the diffs of
  *working* vs *non-working* payloads (bytes that clear the wedge state
  and do *not* brick the board). That comparison is the project's most
  valuable data.
* `tooling/` — capture helpers ported to other distros / BSDs; anyone who
  graphs the wedge *frequency* over time on the same keyboard gets a
  distinct piece of evidence (it varies per unit).
* Add a **keepalive experiment** runner (test mode with vendor-ping sent
  every 30/60 s) — measuring whether idle-wedge *stops* under it is the
  "prevention not cure" evidence this analysis needs.
* Translation of `MASTER-ISSUE.md` into other languages is welcome — reach
  other servo owners of these boards (very common in many countries).

## Ground rules

* **No vendor binaries in the repo** (see `analysis/flash-kit-reference.md`).
* **Don't flash strangers' keyboards**: advice like "download this firmware
  and flash it" is a *brick vector* the community has been burned by before —
  prefer the guard / software-only mitigations.
* Attacks on the *user's* system are not welcome.
