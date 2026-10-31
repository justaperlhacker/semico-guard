# AGENTS.md — context for AI agents / contributors working in this repo

Read this before touching code. It encodes the hard-won context of the Oct
30/31, 2026 forensic session, and the environment specificities that
cost us real time to rediscover.

## What this project is

A small, focused tool for a *very* weird peripheral bug: the Redragon
K552-KRS's SEMICO controller (VID `1a2c`) wedges itself — emits a phantom
held-key bundle `ESC + TAB + GRAVE (+CAPS)` burst (raw HID boot-keyboard
frames, rid 2/3, modifier bits 0x00 in-frame), occasionally repeat-spams,
then drops off the bus. It does this **while completely idle**, in **wired**
and **2.4G** modes. `semico-guard` is the workaround: a root daemon that
watches raw `hidraw`, recognizes the signature, and resets the offending
USB port. See `analysis/MASTER-ISSUE.md` for the canonical defect record,
the byte-level evidence table, and the sister-SEMICO cases.

## Hard environment facts (local machine: destro, CachyOS)

* **Deployment loop**: editing `semico-guard.py` in the repo does *nothing*
  until it's copied to `/usr/local/sbin/semico-guard` and the unit restarted.
  The repeatable one-liner (used ~half a dozen times in one night):
  ```bash
  sudo install -m 755 ~/redragon-firmware/semico-guard.py /usr/local/sbin/semico-guard \
    && sudo systemctl restart semico-guard && sudo journalctl -u semico-guard -n 3 --no-pager
  ```
* **`pkexec` flakiness** under extended sessions (polkit agent hangs / policy
  cooldown churn). When a `pkexec` call hangs >60 s with no password prompt
  on screen: kill the hung `pkexec` process and ask the user to run the
  `sudo` line in their own terminal instead. Don't fight it.
* **`/tmp` does not survive reboots** on this machine. Anything in
  `/tmp/opencode/` (logs, captures, helper scripts) is ephemeral — put
  anything worth keeping in `~/redragon-firmware/` or this repo.
* **`journalctl` is NOT persistent** across reboots (survives only the most
  recent boot(s)). Snapshots of evidence go into `analysis/`.
* **Systemd user services matter**: `kanata` (key remapper) runs as a user
  service and *grabs* all keyboards' evdev nodes exclusively. Consequence:
  **evdev readers see NOTHING from a grabbed device.** That's why the guard
  reads `hidraw` instead (separate channel, unaffected by EVIOCGRAB).
* Multiple hidraw readers get independent copies of the same stream — safe
  to run guard + capture tools alongside.

## Device identity / node numbering gotcha

* Wired: `1a2c:7504` ("SEMICO USB Gaming Keyboard", low-speed, composite:
  iface0 keyboard, iface1 consumer/system/vendor).
* 2.4G dongle: `1a2c:7fff` ("2.4G Wireless Device", full-speed, 3 interfaces:
  iface0 boot-kbd, iface1 consumer, iface2 **vendor** — `resetv2/` target).
* Hybrid USB class: USB devices are `0003:1A2C:...`, BT ones `0005:1A2C:...`
  (`uhid`). The `VENDOR_RE` covers wired+dongle; BT detection is a regex
  widening away but its *reset* is out of scope (no vendor channel over BT).
* **`/sys/class/hidraw/hidrawN` numbers are dynamic** — they change on every
  replug AND across reboots (N = hotplug order). Never hardcode. Match by
  walking sysfs from the hidraw node up until `bInterfaceNumber`.
* **Sorted-glob returns string order — `hidraw10` sorts before `hidraw2`.**
  With the dongle AND the wired board connected, a naive single-node scanner
  silently picks the wrong one. The guard therefore watches *all* matching
  interface-0 nodes (`find_nodes()`). Keep it that way.
* From the interface dir, the USB device dir (carrying `busnum`/`devnum`,
  used to build the reset target `/dev/bus/usb/%03d/%03d`) is *one level
  further up* than people expect: `hidrawN → hidraw/ → HIDdev → interface →
  usbdev`. A one-level-off walk is exactly the v2→v3 bug this file exists to
  prevent.

## Report-ID byte layout (this cost us the 22:10:22 capture)

```
byte0 = report id (0x03 normally, 0x02 variant observed mid-burst!)
byte1 = modifier bits (usually 0x00 in real bursts — do NOT require them!)
byte2 = reserved
bytes3..8 = keys[]
```

Signature (keys-only, verified against all captured wedges): rid ∈ {2,3} and
`{0x29 ESC, 0x2B TAB, 0x35 GRAVE}` ⊆ keys. v1 required modifier bits that are
never set in real bursts and matched nothing. The v3→v4 step removed a bogus
"prune fd when /sys/dev/bus exists" check that also broke on keypress churn.

## Guard behavior contract

* detection → `USBDEVFS_RESET` ioctl on the *specific transport's* usb device
  (~50–150 ms kernel-side; user-visible recovery ~0.2–1 s, same device number,
  no re-pair).
* 3-s cooldown between resets (anti-reset-storm damper) — tunable.
* wired: reset = full cure (MCU context power-cycled). radio: reset re-syncs
  the dongle only; the keyboard-side wedge *persists* (that's the design gap
  `resetv2/` closes via the vendor factory-reset channel).
* restart-safe: unit has `Restart=always`, rescans devices every loop when
  none found (survives replug/reboot/high-sidian rearrangements).

## Testing

* There is a `-`-free module-level import guard (`__main__`) — importing
  `semico-guard.py` for unit tests must NOT hang (v2 originally called
  `main()` at module bottom).
* Replay fixture: the real captured frames live in
  `analysis/evidence-ledger.md`; wedge frames recorded as `0300292b35390000`-style
  hex (there is also `0200292b35390000`, and transitional
  `0300292b35000000`/`0300293539000000` → those analyze as non-wedge is
  CORRECT, matching the "recovered without us" observation).
* "normal typing must not wedge" invariants: any single key (e.g. `E`)
  alone in keys[] must never trigger; neither must `TAB` alone, nor
  `GRAVE` alone. The triple-concurrency is the signature.
* Live-fire testing involves a human at the other end with the physical
  keyboard. Communicate clearly: no surprise flashings, no surprise replugs.

## Do-NOTs

* **No vendor binaries in git** (`.gitignore` enforces; see
  `analysis/flash-kit-reference.md` for the license-safe pointer to Redragon's
  own download page).
* **Don't write *anything* to `hidraw12` (dongle MI_02 vendor iface) ad hoc.**
  Arbitrary vendor reports are exactly how you make a keyboard stop talking
  with zero undo. The vendor command set is only exercised from *captured*
  Redragon-software bytes (see `resetv2/README.md` capture plan).
* **Never advice "just flash this firmware"** to users — see CONTRIBUTING.md
  ground rules; this community has bricked units doing exactly that.
* Don't refight solved battles: the crash is *not* caused by kanata, the
  kernel update, the DE, the HUB, the cable, or Fn+Esc (we tested all; kanata
  was disabled, hub bypassed, cable direct-to-motherboard, bare-footed
  captures — the wedge reproduced identically; kanata only *amplified* the
  symptom and is out of scope).

## Orientation

* `README.md` — user-facing entry; links the canonical defect report.
* `analysis/MASTER-ISSUE.md` — the defect record + roadmap (for agents: your
  TODO dispatch; update statuses only with evidence).
* `analysis/MODE-DIFFERENTIAL.md` — the per-mode behavior record (wired vs
  2.4G vs BT): what the wedge looks like, what the guard can fix per
  transport, measured recovery times, and the measurement matrix that the
  resetv2/keepalive experiments compare against.
* `analysis/evidence-ledger.md` — raw byte ledger; the single source of truth
  for reproduce data.
* `resetv2/README.md` — the capture plan and open questions.
* `tooling/` — kbd-capture / led-watch / evdev-all-capture (used in the
  forensic session; standalone scripts, no service).
* `systemd/semico-guard.service` — the unit, `Restart=always`,
  `WantedBy=multi-user.target`.
* `/etc/systemd/system/semico-guard.service` is a *copy*; changes in repo
  need the deploy loop above.
