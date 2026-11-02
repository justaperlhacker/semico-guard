# semico-guard

**Self-healing driver-layer protection for the Redragon K552-KRS (Kumara) "SEMICO wedge"** —
a controller-firmware crash that emits a phantom held-key bundle
(`LCtrl + LShift + Esc + Tab + Grave + CapsLock`), repeat-spams at ~30/s, and
then drops the keyboard off the bus.

> TL;DR: this keyboard's MCU crashes on its own (even completely idle, any
> connection mode). No existing firmware fixes it (vendor "update to latest"
> is a no-op), no key combo reliably recovers it. `semico-guard` is a small
> root daemon that reads the raw HID stream, recognizes the crash signature,
> resets the USB port from software, and the keyboard comes back in ~200 ms —
> no replugging, no lost session.

## What we know about the crash (byte-level evidence)

Recovered from raw `hidraw` taps on the keyboard (and its 2.4G dongle), with a
`signature (*)` shared between *all* observed wedge events while the machine
/idle/ sat completely untouched:

```
boot-keyboard report, bare report id 0x03 (and a 0x02 variant appeared mid-burst):
    byte0      = report id
    byte1      = modifier bits (usually 0x00 in real bursts!)
    byte2      = reserved
    bytes 3..8 = keys[]

Signature (keys-only): rid ∈ {2,3} and
    {0x29 ESC, 0x2B TAB, 0x35 GRAVE} ⊆ keys[]       (Caps 0x39 usually rides along)
```

Sample bursts, byte-hex, every single one **while the keyboard sat idle**:

| timestamp | raw frame                                        | notes |
|---|---|---|
| 21:57:46 | `0300292b35390000` | first radio-path wedge, LED lit |
| 22:10:22 | `0300292b35000000` `0300292b35390000` `0200292b35390000` `0300292b35390000` `0300293539000000` | full multi-frame burst, rid 03/02 alternate, self-recovered in 0.18 s |
| 22:17:48 | `0300292b35390000` | plain |
| 23:52:19 | `0300292b35390000` (x5 over 8 s)    | held-bundle repeat pattern, wedge phase |
| 00:14:38 | `0300292b3539...` (over 2.4G dongle!) | guard fired USBDEVFS_RESET, keyboard recovered in ~200 ms without a single key press |
| 13:42:20 | `0300292b3539...` `0300292b353952...` | radio wedge storm; guard fired 3 resets; ghost keys *persist over radio* because the reset re-syncs the dongle only — MCU state needs the keyboard-side reset |

Every crash reproduced **with no keystrokes fed to it**, on *all* connection
modes (wired USB, 2.4G dongle). The mode selector is irrelevant — it's the
SEMICO controller's own firmware doing this, not Linux, not the DE, not a key
combo, not `kanata`, not vn/a your hub. The Linux side merely *sees* it.

Full forensic tale: [analysis/MASTER-ISSUE.md](analysis/MASTER-ISSUE.md) —
the canonical defect report + workaround + roadmap; the **per-connection-mode
behavior record** in
[analysis/MODE-DIFFERENTIAL.md](analysis/MODE-DIFFERENTIAL.md); raw byte
ledger in
[analysis/evidence-ledger.md](analysis/evidence-ledger.md); investigation
snapshot in
[analysis/k552-keyboard-investigation-snapshot.md](analysis/k552-keyboard-investigation-snapshot.md).

## What semico-guard does

1. **Detection (`semico-guard.py`)** — single root process, polls `hidraw`
   (not evdev — so it sees the *raw* stream under `kanata`-style input
   filters), multi-transport (wired +2.4G dongle), systemd-managed, verbose
   journald logging with per-transport attribution.
2. **Auto-recovery** — on hit: fires `USBDEVFS_RESET` on the exact port the
   crash rode in on. Over *wired*, MCU context power-cycles clean — fully
   reliable. Over *2.4G radio*, the reset re-syncs the dongle and clears the
   ghost-KEB stream but the *keyboard's stuck internal state* needs its own
   reset — see `resetv2/`.
3. **Ledgering** — every wedged hit is recorded with timestamp, transport and
   raw frame hex, so repeated blasts are cheap evidence for a support ticket.

## Install

```
git clone <this-repo>
cd semico-guard
sudo ./install.sh
```

`install.sh` copies `semico-guard.py` to `/usr/local/sbin`, installs the
systemd unit, enables + starts it. Detects only VID `1A2C` / PID
`{7504 (wired), 7FFF (2.4G dongle)}` — safe to leave running on machines
without the keyboard (it idles and rescans on hotplug).

System paraphernalia stays user-configurable; the daily-run
`journalctl -u semico-guard -f` line is:

```
semico-guard: [/dev/hidraw10] frame 0300292b3539... -> HIT
semico-guard: WEDGE SIGNATURE -> resetting /dev/bus/usb/001/015
semico-guard: USBDEVFS_RESET ok
```

## Bluetooth support

- **Detection: SHIPPED (guard v5, 2026-11-02).** BT-paired K552s enumerate
  as `0005:1A2C:7FFF` via `uhid` (same SEMICO identity — nice); BT frame
  layout differs (no report-id byte) and the guard dispatches per-source.
- **Auto-reset: NOT possible over BT.** Live verification: the BT HID node
  exposes a single hidraw (no vendor interface composition), i.e. the
  factory-reset channel is absent — matching Redragon's own "software not
  available in Bluetooth mode". On a BT wedge the guard *journals* it and
  logs the instruction to power-cycle via the belly switch; the physical
  replug fallback applies only to the wired path.

## Why is this a repo?

The off-the-shelf K552's own software (the "Software Update" button) reports
"already on the latest version" while this crash is real; the bug appears to
be shipped instability in the SEMICO `keyboard-700/704K` firmware family. This
repository makes the workaround reproducible for anyone with the same
keyboard, and centralizes the evidence needed by anyone filing the RMA /
support ticket.

**Development status:** v1 (multi-transport wedge detection + wired auto-recovery)
is live and battle-tested on the author's machine. `resetv2/` — the
over-the-air factory reset via the dongle's vendor channel — is in progress.
Issues/PRs welcome; hardware-wise, if you own a K552-KRS and see the same
`Esc+Tab+Grave+Caps` phantom on *your* unit, the author would love your
capture data.

## License

GPL-3.0-or-later — see [LICENSE](LICENSE).
