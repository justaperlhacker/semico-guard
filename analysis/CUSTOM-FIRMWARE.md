# Custom firmware for the K552's SEMICO controller — feasibility record

> Filed here for the future. Not a commitment — a *declassified playbook* of
> what making our own firmware for this chip would actually require, what we
> already know, and which single capture tonight decides its viability.

## TL;DR

Building replacement firmware for the SEMICO controller inside the K552-KRS
is **currently blocked on vendor closure**, not on our skill set, and
**probably involves a COB (chip-on-board) package** that also carries the
BT/2.4G radios' stack, which is one-more-layer of exposure. There is **one
cheap, future-deciding capture** in tonight's session: recording Redragon's
own firmware *flashing session* over `usbmon` hands us the undocumented ISP
protocol in plaintext; if that protocol is plain and re-flashable (cheap
vendors often are), a "safe write" path and eventually a wedge-free /
custom image becomes a multi-month but *bounded* project. If the protocol is
encrypted or security-locked (Code Security flags set), the project is
closed for all practical purposes.

## What the SonixQMK precedent proves (and why it doesn't apply yet)

The **SONIX SN32** MCU family — used by *other* Redragon keyboards (K530,
K552-RGB v1, K556, Womier, Keychron…) — has a thriving open firmware
ecosystem:

* **SonixQMK** (`qmk_firmware` fork): QMK ports for many Redragon boards,
  including a *jumploader* community bootloader to protect the ISP.
* **SonixFlasherC**: community USB flasher for SN32F248/F268.
* **Public datasheets** (e.g. SN32F268 user's manual from sonix.com.tw) that
  spell out the flash, ISP (writer tool "SN32F268 Writer"), USB block and
  even the **Code Security** model.

That ecosystem exists **only because Sonix publishes the datasheet and the
ISP contract is public**. The community could port QMK because every
requisite piece was on the table.

**SEMICO (China Resource Semico, VID `1a2c`) publishes none of that.** No
datasheet, no SDK, no documented ISP, no public Code Security statement, and
no community tooling — just *watermarks of one* in unrelated products
(the Hantek scope repo ships a "Semico Writer" for *their* scope chip).
Our board's own identities:

* wired: `1a2c:7504` "SEMICO USB Gaming Keyboard" (composite: iface0
  boot-kbd, iface1 consumer/system/`,vendor`)
* dongle: `1a2c:7fff` (3 interfaces, one of them vendor)
* ISP/bootloader mode: !! `1a2c:7f08` (discovered by disassembling the
  vendor flasher) — so an ISP **exists**, silently.

## What we'd need to even attempt a custom image

1. **Chip identification** — open the unit and read the controller package.
   On this price class it is quite likely **COB (bonded die)**: if so, no
   marked part number, no programming pins, and *no* practical way to
   program anything without bonding equipment (a dead end for hobby
   hardware surgery). If it is a marked SOIC/QFN — capture the markings;
   that alone may reveal the core (8051-class or Cortex-M0) and possible
   known development tooling.
2. **Data sheet / core info** — either from the part number, or by
   deduction: we can already infer rough behavior from the USB IRQ
   patterns (low-speed HID, watchdog-style behavior per the montech
   sister case), but the *toolchain* for an unknown 8051/M0 variant is not
   a guessable quantity.
3. **ISP protocol** — **this is tonight's decisive capture**: when
   Redragon's `700N(0X3B4F)defineV9` flasher writes firmware in the VM, the
   host-side `usbmon` tap records the whole bootloader session (the
   `1a2c:7f08`-period traffic) *byte for byte*. Commands, block sizes, page
   addresses, write formats, CRCs — all of it, for free.
   `IF this is plaintext, everything below becomes a bounded project.`
4. **Firmware *content*** — even with the ISP working, we need firmware to
   write:
   * a **patched stock image** (derive one from the vendor's `defineV9` blob
     + a targeted patch that neutralizes the wedging code path: this is the
     *low*-risk "surgical" variant and probably un-shippable to other users
     because the compound contains vendor code), or
   * a **from-scratch QMK-style firmware** ported to this chip's USB block —
     high effort, and it forfeits the radio modes unless the BT/2.4G stack
     is separately understood (on a tri-mode chip, the radio stack might be
     *inside the same image*; a custom image may permanently lose BT).
5. **Brick-resistance** — the community's Sonix path eventually added a
   *jumploader* because bricking became cheap and common. For SEMICO we
   would need the same safety design **before** any real flashing,
   e.g. first flash must leave the bootloader untouched and be performed
   with a physical *re-plug* fallback that we've verified exits cleanly.

## Minimal viable experiment ladder (if we ever go this way)

| step | action | success criterion |
|---|---|---|
| E1 | capture the *stock* flashing session (same capture as resetv2 tonight) | ISP frame format is plaintext |
| E2 | **read-back** experiment: if a read command exists in the captured protocol, dump the stock image via the bootloader | recovery image in hand (level: important!) |
| E3 | write-back experiment: re-write the *stock* image byte-for-byte via the bootloader | board still works → ISP is fully understood |
| E4 | patch experiment: binary-patch the stock image (e.g. NOP out the wedge branch we've located dynamically — see `analysis/evidence-ledger.md`) and write | wedge gone, board works → **the defect is fixed at firmware level** |
| E5 | (optional, much later) clean-room QMK port to the chip | definitive, shareable replacement image |

E2/E3 are the *gate* steps: without a read-back or byte-identical write-back
that survives, the whole path is too risky to pursue (a one-way write with no
recovery image on a $45 keyboard is an acceptable *one-time* gamble, not a
development methodology).

## What's cheap to get *now*

* The E1 capture is **identical to the resetv2 capture session** — one night,
  one recording, no extra work.
* If the flasher protocol turns out plain: archive the *entire stock image*
  the flasher pushes (`defineV9`) — that's the **recovery image** nothing
  official publishes.rs
* Even without any firmware write ambition, the E1 capture *documents the
  bootloader*, which doubles as evidence that the vendor ships an ISP we can
  use (RMA letter supports "the tooling exists; it's just closed").

## Where we're likely NOT going

* **BT/2.4G radio stack**: a custom image would almost certainly forfeit the
  wireless modes. If the keyboard is used primarily by cable after a custom
  flash, that's acceptable—but say it out loud: the wireless trunk is likely
  *inside* the SEMICO image we'd be replacing.
* **Code Security**: if the captured flashing session shows CS/lock bits
  being set/re-armed, the chip may forbid reading back *anything* — E2 dies
  on contact. Again: the capture decides.

## Decision rule

> After tonight's capture session: if the ISP traffic is plaintext and
> page-addressable → **archive the recovery image**, park this file as
> "feasible, waiting for a volunteer with a sacrificial unit". If the ISP
> traffic is opaque/encrypted → **close this file as infeasible without chip
> insider access**, re-anchor the project on resetv2/keepalive and be done.
