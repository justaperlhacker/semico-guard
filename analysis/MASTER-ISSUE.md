# SEMICO wedge — master issue (defect report + workaround)

> **Status: OPEN — workaround available (semico-guard), root-cause fix pending upstream.**
> This file is the canonical record of the defect we live with and the
> roadmap we're working, so people arriving here from a search can find
> the state of the world in one place.

## The defect

Redragon K552-KRS (Kumara, tri-mode: wired / 2.4G / BT) randomly enters a
wedge state in which the onboard **SEMICO controller** (VID `1a2c`) floods
the host with a phantom held-key bundle:

```
boot-keyboard frames: rid ∈ {0x02, 0x03}
keys: {0x29 ESC, 0x2B TAB, 0x35 GRAVE} + 0x39 CAPS (modifier bits 0x00)
```

…repeat-spams at ~30 Hz on the last key, lights the CapsLock LED, and then
drops the keyboard off the bus (or over the 2.4G dongle, floods until the
*keyboard's own timer* gives up). Reproduces **completely idle** (hands off
keyboard) and in **all connection modes** (wired USB and radio verified).
Linux cannot fix it: the data is *generated inside the controller*.

Byte-level forensics: [`analysis/evidence-ledger.md`](analysis/evidence-ledger.md).
Investigation snapshot: [`analysis/k552-keyboard-investigation-snapshot.md`](analysis/k552-keyboard-investigation-snapshot.md).

## Why this is not the user's fault

* Reproduces across: hub port / direct motherboard port, wired / 2.4G,
  multiple boots, multiple distro/kernel configurations, with our own driver
  stack, with the SINO WEALTH keyboard as control (control unit: **0** wedges
  during the full soak).
* The phantom bytes are *emitted by the board*, and the OS never sends
  anything that could trigger it (verified byte captures on both transports).
* Upstream Redragon's upgrade server reports our shipped firmware
  (`defineV9 20260316`) as "already latest" — no fixed build exists.

## Workaround (what actually works today)

[`semico-guard`](../README.md) — root daemon:

* watches raw `hidraw` (unaffected by kanata-style grabs), matches the
  signature, fires `USBDEVFS_RESET` on the offending port:
  * **wired mode**: *full cure* (port reset power-cycles the MCU context) —
    wedge resolved in ~0.2–1 s, zero user impact;
  * **2.4G mode**: reset re-syncs the *dongle* only, so the wedge can persist
    keyboard-side — the guard still logs everything (evidence!) and damps the
    flood, but the ghost state typically outlives the reset (the radio-path
    hole this project's `resetv2/` aims to close).

Install: `sudo ./install.sh` (see README). Live log:
`journalctl -u semico-guard -f`.

## Roadmap (in progress — tracked here)

| # | Item | Status |
|---|---|---|
| 1 | Vendor-command capture (USB `usbmon` + KUMARA in VM, English UI) → `resetv2/captured-vendor-commands.md` | pending tonight |
| 2 | `resetv2/factory-reset-over-dongle.py` — replay the `Restore Factory Settings` payload into `hidraw12` (`1A2C:7FFF` MI_02) to clear a wedged MCU **over the radio** | pending #1 |
| 3 | Guard second stage (optional, config-gated): wedge on dongle → dongle reset → if frames continue > 3 s → send command #2 over the air | pending #2 |
| 4 | **Keepalive experiment** (hypothesis from sister case): SEMICO firmware has a *watchdog* that misbehaves when host vendor traffic is quiet (documented for `1a2c:4e85` in montech's cooler driver) → send a benign vendor ping every 30–60 s; if idle wedges *stop*, we have prevention, not just cure | designed; run after #2 |
| 5 | Publish evidence to sister-victim channels (Fedora `1a2c:7807` thread, r/linux4noobs `1a2c:4094` thread, `dokutan/rgb_keyboard#26` cross-link) — first byte-level public record anywhere | pending |
| 6 | RMA packet (`analysis/*` byte ledger + transport-dual repro) if the keyboard's warranty still applies | optional |

## Related cases (sister keyboards / SEMICO family)

* `1a2c:7807` — "SEMICO USB Gaming Keyboard" self-drops every 5 s on Linux
  6.18 (Fedora discussion, Jan 2026) — same interface layout, same
  `bcdDevice 1.11`, same vendor line: **our wedge, sister PID**.
* `1a2c:4094` — "External USB keyboard partially dies" (r/linux4noobs) —
 Semantic suite was asking our exact question ("is there a known HID
 descriptor bug?").
* `1a2c:9cf4` — "USB Gaming Keyboard" that enumerates (bcdDevice 0110, the
 *exact same identity* as our K552-KRS!) but emits **no HID reports**
 (tinyusb discussion, 2024) — SEMICO's USB HID stack demonstrably brittle
 on sibling silicon.
* `1a2c:4e85` — SEMICO "USB Gaming Keyboard" inside the Montech HyperFlow
 cooler: firmware has a **watchdog** gone wrong when host vendor writes stop
 (~1 s timeout) — *structural explanation for our idle-triggered wedges*.

## Search terms

`redragon k552 phantom keys` · `redragon stuck ctrl shift tab grave`
· `k552 wedge` · `semico keyboard ghosting` · `1a2c:7504 wedge`
· `k552-krs random keys pressed` · `kumara ctrl+shift+t broken`

If you found this page via any of those — **you are not alone; this board's
firmware does this to people.** Add your data (see
[CONTRIBUTING.md](../CONTRIBUTING.md)): attach your `semico-guard` journal
(`journalctl -u semico-guard -b -1` whatever mode you're in) and your exact
model string from `lsusb`.

