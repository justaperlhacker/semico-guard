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
| 5b | **BT mode: shipped** — user paired the board over BT (more stable, still wedges occasionally); guard v5 detects BT wedges (`0005:1A2C:7FFF`/uhid) & journals them. Cure impossible over BT (vendor channel absent — verified live). Detection-only, like the roadmap predicted | **shipped 2026-11-02** |
| 6a | **Vendor support email sent → support@redragon.com (Nov 2, 2026)** — byte-evidence report + firmware request + warranty-case question (letter: `analysis/vendor-support-email.md`; composer page: `analysis/vendor-support-email.html`). Awaiting reply; follow-ups: diff any received firmware vs `defineV9` (sha256 `728f97e5…`), record vendor acknowledgment in this ledger | ⏳ awaiting reply |

## Rung items (the custom-firmware ladder — FILED as future work)

All three rungs of the ladder are now **documented and slated as future work**
in [`analysis/CUSTOM-FIRMWARE.md`](analysis/CUSTOM-FIRMWARE.md) — the file
outlines the honest feasibility (blockers: vendor closure, likely COB
packaging, unknown Code-Security state) and the *experiment ladder* that
turns it from vaporware into a bounded project **only if tonight's E1
capture reveals a plaintext ISP protocol**:

* **Rung E1 — capture the vendor ISP session** *(shared with Item 1 above —
  same recording, zero extra work)*. Records Redragon's own flasher driving
  the `1a2c:7f08` bootloader byte-for-byte. Gate: protocol plaintext?
* **Rung E2/E3 — read-back / byte-identical write-back** *(future)*. With a
  working read-back we archive a **recovery image** (nothing official
  publishes one); with write-back verified, the chip is fully understood.
  Gate: no Code-Security lock in the captured session.
* **Rung E4 — patch stock image** *(future)*. Locate the wedge branch
  dynamically and NOP it in the stock `defineV9` image; flash once.
  This would **fix the defect at firmware level** with the *vendor's own
  code* (not redistributable, but it fixes *our* board). Only afterwards
  would the much bigger quest (clean-room QMK port to this unknown chip,
  Rung E5) even be considered.

Decision rule (from `CUSTOM-FIRMWARE.md`): if E1's ISP traffic is plaintext
and page-addressable → archive the recovery image and park the file as
"feasible, waiting for a sacrificial unit". If it is opaque/encrypted →
close the file as infeasible without vendor insider access and re-anchor the
project on resetv2/keepalive.

## Long-arc item: our own SEMICO firmware (future, high-effort)

Filed as a **future-work** item — see [`analysis/CUSTOM-FIRMWARE.md`](analysis/CUSTOM-FIRMWARE.md)
for the honest feasibility analysis. Short version: building a replacement
firmware for this chip is blocked on vendor closure (no datasheet, no SDK, no
public ISP spec, likely COB packaging), BUT the door isn't welded shut:

* The board *has* an ISP bootloader mode (re-enumerates as `1a2c:7f08`).
* Redragon's own flasher drives that bootloader over HID — and when it does,
  a `usbmon` host-side tap will record the **entire ISP session in
  plaintext**. That capture is the *decisive* datapoint: if the protocol is
  plain (cheap vendors often are), a "safe firmware write" path becomes
  possible in future, and with it a truly wedge-free image.
* The capture for #2 and the ISP capture are the **same recording** — one
  session, both artifacts. Step 2 of the tonight-session already collects it.

Nothing in this item is load-bearing for the working keyboard: rungs 1–3 of
the table are the practical fix; this only matters if we ever choose the
"surgical" path or a future donor unit appears.


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

