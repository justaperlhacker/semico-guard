# Mode-differential findings — how the wedge behaves per connection mode

> Companion to [`evidence-ledger.md`](evidence-ledger.md) (per-event raw
> frames) and [`MASTER-ISSUE.md`](MASTER-ISSUE.md) (the roadmap). This file
> organizes our observations **by connection mode**, so that later work
> (resetv2, keepalive, RMA, custom firmware) can compare apples to apples.
> All entries reference timestamped guard/kernel evidence.

## Summary decision table (state as of 2026-10-31)

| Mode | Boards seen wedging? | Guard detection | Guard cure? | Manual recovery | Recovery time (observed) |
|---|---|---|---|---|---|
| **Wired** (`1a2c:7504`) | ✅ 6+ events | ✅ instant | **✅ full cure** (port reset reboots MCU) | none needed | **~0.2–1 s** (1 reset, 1-and-done) |
| **2.4G radio** (`1a2c:7fff` dongle) | ✅ 3 events (incl. 1 storm) | ✅ instant | ⚠️ **partial** (resets the *dongle* link only; keyboard state persists) | belly switch OFF→ON (MCU power cycle), physical replug, KUMARA over dongle (rest of this repo) | **~10 s** (self-clears occasionally) to **minutes** (needs manual) |
| **Bluetooth** (`0005:1A2C:7FFF` via uhid) | ✅ live (paired, name `BT 5.0-2`), more stable per user report but still wedges occasionally | ✅ **shipped in v5** (journal + transport stamped) | ❌ **no remote cure possible** — vendor channel absent over BT (Redragon docs; verified live: BT HID has 1 hidraw node, no MI_02) | belly switch OFF→ON (MCU power cycle) | first BT wedges journaling now; recovery unmeasured |

Conclusion so far: **wired is the mode with a complete cure today**;
radio needs the resetv2 vendor-reset (or manual) to match; BT is
detection-only by design.

---

## WIRED mode (`1a2c:7504`, "SEMICO USB Gaming Keyboard", low-speed)

* Identity: composite; iface0 boot-kbd (keyboard), iface1
  consumer/system/**vendor** (`MI_01`, the KUMARA app's channel).
* Behavior per wedge: 1-frame bursts (sometimes 2–5 frames over 0.2 s), or
  held-bundle repeats (~2 s apart during one storm), LED flips (self-driven
  CapsLock LED — host is not involved), and **sometimes a full drop of USB**.
* Guard action: `USBDEVFS_RESET` on the *keyboard's* usb device.
  Because the port reset power-cycles the *whole MCU*:
  - ghost keys die instantly;
  - the board re-enumerates with the **same device number** (no re-pairing);
  - kanata-style grabs (if any) re-register transparently;
  - one reset, no repeats ("1-and-done" behavior, every wired wedge we've
    seen).
* Recovery: **~0.2–1 s total**, verified repeatedly with journal + kernel
  timestamps.

## 2.4G radio mode (`1a2c:7fff`, "2.4G Wireless Device", full-speed dongle)

* Identity: the *dongle* enumerates (full-speed, 3-consumer composite); the
  keyboard is battery-powered and unreachable by bus resets.
* Behavior per wedge: identical bundle frames (the same `Esc+Tab+Grave+Caps`
  signature crossed over the radio!), **sometimes a storm** (frames every
  ~1–10 s, sometimes lasting ~1–2 min), each storm self-clears eventually OR
  persists until the keyboard state is reset.
* Guard action: `USBDEVFS_RESET` on the **dongle** device. This resets the
  radio link, but the *keyboard MCU keeps running* (battery-powered) with
  its stuck state — so:
  - ghost frames *continue* arriving after each reset (documented: 3 resets
    across the 13:42 storm, each followed by more wedge frames);
  - detection/ledgering still works at full fidelity (all wedge frames land
    in the journal with their hex — all firms the config-level fault is
    inside the SEMICO MCU, *not* the USB transport);
  - recovery = "whenever the keyboard's own logic gives up" — observed
    ~10–60 s — **or** when the user intervenes.
* Manual recovery options (documented for completeness):
  1. **Belly switch OFF → 2 s → back to 2.4G** — *real* MCU power-cycle
     without touching the cable; recommended rescue method.
  2. Physical replug of the USB cable (slower, does NOT reset the MCU
     automatically — the cable is only for data/charge; the *mode selector*
     decides).
  3. KUMARA "Restore Factory Settings" *through the dongle* — possible per
     vendor's own config (mode 2.4G/TYPE_A  maps to `1A2C:7FFF`), but
     requires the VM/app stack → *this is exactly what `resetv2/` is
     building*: the same command replayed from Linux into `hidraw12`
     (dongle MI_02), turning this manual rescue into an automatic one.

## Bluetooth mode — **live since 2026-11-02, guard v5 ships detection**

* Paired today as `BT 5.0-2` (`1B:9C:46:46:8D:CE`); HID arrives via `uhid` as
  `0005:1A2C:7FFF` — SEMICO identity *is* preserved over BT (nice finding:
  the BT HID descriptor identifies the same vendor/product as the dongle).
* BT frame layout **differs from USB** (captured live, see
  `bt-hidraw-snapshot.log`): `[mods, reserved, keys...]` — *no report id*
  byte. The guard's `analyze()` now dispatches per-source (node `bt` flag).
* **Vendor channel is ABSENT over BT**: the BT-connected HID exposes only
  one hidraw node (no MI_01/MI_02 composition, unlike the USB paths) —
  i.e. **no remote factory-reset is possible over BT**, which confirms
  Redragon's own "software not available in Bluetooth mode" statement.
* User experience (Nov 2): BT mode is *more stable* than wired/2.4G, but
  still stucks occasionally. The guard now journals those wedges with the
  BT transport stamp; manual rescue remains the belly-switch power cycle.


## Measurement matrix — counts & key events (through 2026-10-31 14:45 EDT)

| Event | Mode | Result |
|---|---|---|
| 21:57:46 | wired | 2-frame burst, self-recovered, LED lit |
| 22:10:22 | wired | 5-frame burst (rid3+rid2 mix), self-recovered in 0.18 s |
| 22:17:48 | wired | 1-frame burst |
| 23:52:19–:27 | wired | 5 frames over 8 s (held bundle repeats) |
| 00:14:38 | **dongle** | 1 frame → guard reset → **auto-healed** (rare: single wedge state cleared itself over radio) |
| 13:42:20–:42 | dongle | storm; **3 guard resets**; ghost frames continued between resets; user finally rescued by replug |
| 13:54:51 | dongle | 1 frame → reset ok; 2 follow-up frames swallowed |
| 14:43:57–:09 | dongle | 8 frames / resets×2; user report: "takes a while to get back into functional mode" (~10+ s) |

* Firmware fixed? Upstream says "already latest" — no. (Vendor's own
  update server reports shipped `defineV9 20260316` as current.)

## What this differential record is for

1. **RMA / support-packet**: two transports with *the same* byte signature is
   what proves the defect is in the chip's firmware, not Linux/hub/cable.
2. **Resetv2 testing baseline**: when the over-the-air reset lands, we
   compare storm length before (baseline above) vs after (should be
   ~1 reset per wedge, same as wired).
3. **Keepalive-experiment baseline**: if a periodic vendor ping *stops*
   the idle wedges, expect the wired and dongle curves to flatten together
   (and this file becomes a "before" snapshot).
