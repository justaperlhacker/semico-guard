# Wedge evidence ledger (raw HID frames, byte-level)

All frames captured from raw `hidraw` reads on the SEMICO keyboard's
boot-keyboard interface (iface 0). Timestamps local EDT, 2026-10-30 →
2026-10-31.

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
