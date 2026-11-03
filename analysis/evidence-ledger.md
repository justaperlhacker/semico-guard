# Wedge evidence ledger (raw HID frames, byte-level)

All frames captured from raw `hidraw` reads on the SEMICO keyboard's
boot-keyboard interface (iface 0). Timestamps local EDT, 2026-10-30 →
2026-10-31.

## THE GHOST BUNDLE EXPLAINED — it is the keyboard's matrix COLUMN 0 (verified 2026-11-03)

**The app's own factory layout file** (`kb-k600t.xml`, extracted from the
KUMARA app; the `row_col` attribute maps the physical scan matrix) places
these keys on **matrix column 0**:

| row_col | key | HID usage |
|---|---|---|
| 0#0 | **Esc** | 0x29 |
| 1#0 | **` ~ (grave)** | 0x35 |
| 2#0 | **Tab** | 0x2b |
| 3#0 | **CapsLock** (+ a duplicate "L" slot) | 0x39 |
| 4#0 | **Shift** (code 0xe1) | modifier bit 0x02 |
| 5#0 | **Ctrl** (code 0xe0) | modifier bit 0x01 |

Cross-check with everything we recorded:
* the ghost bundle's *keys* = **Esc + Grave + Tab + Caps** = the FOUR typing
  keys of column 0;
* the phantom modifier traffic = **LShift + LCtrl held** = the two modifier
  keys of column 0;
* over BT the ghost frames carry modifier bits *2|1 set* (0x03 = the two
  modifiers) and *modifier* prefixes (01) — i.e. **over BT, the firmware
  honestly reports the column's modifier keys as active**.

**Every wedge session we recorded, across wired and 2.4G and BT transports,
matches exactly what a *stuck scan of matrix column 0* produces.** This is
a hardware-defined signature, user-independent:

* the user's typing habits are irrelevant — the ghost set is the *matrix*
  set (the reporter does not press ` ~ at all, yet the bundle always
  includes it);
* the wedge fires whether the user is pressing keys or not (idle or
  mid-typing): the *scan line* is what glitches, not a key chord;
* the same four keys appear every time, across days, on all transports —
  a scanning state that is local to that column.

## Why this points *inside* the firmware (and why the LEDs matter)

The CapsLock LED (the red light next to A during wedges) is driven on the
same scan cycle — the LED controller shares the MCU's scan timing. The
windows where the wedge most often fires are those *with lighting state
changes* (Fn+Space toggles, lighting auto-cycles, the power-on backlight
sweep): the intervals where a *lighting update can overlap the start of a
scan pass* (column 0 is scanned *first*). A race there would:
* read the whole column as pressed (our ghost bundle);
* flicker LEDs (the Caps LED the user saw lit with no host involvement);
* drop the *entire* scan/USB session logic into a bad state (the wedge).

## The ghost bundle

`rid ∈ {0x02, 0x03}`, `keys[]` containing `{0x29 ESC, 0x2B TAB, 0x35 GRAVE}`
(usually with `0x39 CAPS`) — with modifier bits `0x00` inside the frame
itself. The LCtrl/LShift the *OS* later sees arrive separately / via separate
frames (see "modifier trail" below). This bundle reproduces **while the
keyboard is idle**, in wired mode AND over the 2.4G dongle.

## Verified raw frames

| exact hex | meaning |
|---|---|
| `0300292b35390000` | rid3, mods=0, keys = ESC Tab ` Caps |
| `0300292b35000000` | rid3, mods=0, keys = ESC Tab ` (transitional, no caps) |
| `0200292b35390000` | rid2 variant, same keys |
| `0300293539000000` | rid3, keys = ESC ` Caps (tab released mid-burst) |

## Observed wedge events (2026-10-30/31)

| when | transport | frames | outcome |
|---|---|---|---|
| 21:57:46 | wired (`hidraw0`, Dev 40)  | 2 frames / 1 s | self-recovered, LED lit |
| 22:10:22 | wired | 5 frames / 0.2 s | self-recovered (0.18 s) |
| 22:17:48 | wired | 1 frame | self-recovered |
| 23:52:19–:27 | wired (post dongle-in) | 5 frames over 8 s | held-bundle; manual redoes |
| 00:14:38 | **2.4G dongle** (`hidraw10`, Dev 15) | 1 frame | **auto-recovered by guard** (`USBDEVFS_RESET ok`) |
| 13:42:20–:42 | **2.4G dongle** | burst + `0x52 UP`/`0x10 M`/`0x05 B` interleave | 3 × guard resets; ghost state persisted; needed physical replug |
| 13:54:51 | **2.4G dongle** | 1 frame → guard reset ok; 2 follow-up frames swallowed before self-clear | |
| 14:43:57–:44:09 | **2.4G dongle** | 8 frames / **guard resets ×2** / no disconnects | user: "takes a while to get back into functional mode" (~10+ s) — radio-mode baseline |
| **Nov 2 13:17:57 + 13:18:07** | **Bluetooth** (`0103 0029 2b35 39…` = `[mods LCtrl-down][rid3][mods 0x03][keys…]`) | 2 frames 10 s apart — **third ghost encoding found**: BT rides a modifier-frame prefix and sets modifier bits *inside* the rid3 bundle (unset over USB!) | guard v5 caught live; user experienced the stuck state |

* **BT frame shapes** (see `bt-hidraw-snapshot.log` — BT boot report `[mods,
  res, keys…]` with *no report id byte*; and the ghost variant riding the
  rid-3 bundle *with* modifier bits set — see above). The guard's analyzer
  dispatches per-source and tolerates both layouts since v5.1.
* **BT link drop accompanying the wedge**: the BT evdev recorder died with
  `OSError 19 (No such device)` right when the wedge hit — the wedge can
  also drop the *Bluetooth* link, not just over USB. Another data point for
  "the wedge is in the MCU, spanning every transport it speaks."

→ Per-mode recovery summary: [`MODE-DIFFERENTIAL.md`](MODE-DIFFERENTIAL.md).

## Modifier trail (the phantom keys at the OS level)

The kernel-side evdev ledger of earlier wired wedges additionally recorded
`LCtrl + LShift` *down* events (plus Tab, Grave, Caps presses, one Esc). So
the MCU emits both a keys-only burst **and** separate modifier-line traffic;
the guard matches the keys-only subset because it is the *only* reliable
in-frame pattern (modifier bits are `0x00` in the ghost frames).

## Flash-root URL (vendor's own software stack)

* app: `Redragon K552-KRS` device_type=201, device_info=kb-k600t
* upgrade: `https://upgrade-1318931438.cos.ap-beijing.myqcloud.com/keyboard-700/704K/...`
  (server reports firmware "already latest" for our defineV9 2023-03-16 image)

## Firmware identity

* Wired: `1a2c:7504` ("SEMICO USB Gaming Keyboard", low-speed)
* 2.4G dongle: `1a2c:7fff` ("2.4G Wireless Device", full-speed, 3 interfaces:
  boot kbd / consumer / **vendor**)
* BT: not exercised (see resetv2/README.md — vendor channel presumed absent)
