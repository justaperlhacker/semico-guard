# Power management record — host-side fleet state (as of 2026-11-02 15:5x)

**Context:** user's daily driver is now the K552-KRS over **Bluetooth**
(via the TP-Link UB500 adapter). This file is the *configuration ledger*
of every power-management knob we touched, what it was, what we changed,
and what conclusions can be drawn from the effect.

## Fleet snapshot (before changes)

| Device | USB id | dir | `power/control` | autosuspend | Notes |
|---|---|---|---|---|
| TP-Link UB500 (BT adapter) | `2357:0604` | `1-11` | **auto** | **2 s** | the *only* active-power-managed device while BT-only |
| K552 wired / dongle | `1a2c:7504` / `1a2c:7fff` | (not connected in BT-period) | `on` whenever connected | — | runtime PM disabled by default on our ports |

## Change candidate (host-side PM disable)

```
# quick fix (until reboot):
sudo sh -c 'echo on > /sys/bus/usb/devices/1-11/power/control'
# persistent udev rule (K552 BT experiment — applies only to this adapter):
/etc/udev/rules.d/90-tplink-ub500-nopowersave.rules:
  ACTION=="add", SUBSYSTEM=="usb", ATTR{idVendor}=="2357",
    ATTR{idProduct}=="0604", ATTR{power/control}="on"
sudo udevadm control --reload && sudo udevadm trigger
```

**Rationale:** with `control=auto` the adapter *itself* suspends 2 s after
its last USB exchange. Every subsequent BT keystroke must resume the USB
device first; a resume race could be the reason BT-mode wedges *dropped
the link* (evdev recorder died `OSError 19: No such device` at the same
moment the wedge signature fired, Nov 2 13:17).

**What it does NOT change:**
* the K552's *own* idle sleep timer (peripheral-power; the keyboard keeps
  going to sleep on its own — the host cannot disable that; only a **keepalive
  ping over the LED channel** (write a keyboard LED status report on the BT
  hidraw every 30–60 s) can substitute — that experiment is designed in
  `analysis/MODE-DIFFERENTIAL.md`).
* the *power-management* of the K552 wired/dongle paths — the guard covers
  those with `USBDEVFS_RESET` already (and wired `power/control` was already
  `on`).

| Observation after the PM flip (Nov 2, ~16:00 → 23:38 soak) | Interpretation |
|---|---|
| BT wedges **continued** — 9 HITs / 7 events (19:34, 22:23 ×4, 23:20, 23:31 ×3), **several mid-typing** (user: "it was happening mid typing" during coding/game sessions) | host PM (adapter autosuspend) is **exonerated**: wedges fire with the adapter awake, mid-burst of active typing — the keyboard's own 1–2 min idle sleep can't have triggered *mid-typing* either. The remaining model: an **internal race in the SEMICO MCU** (scan/LED/Fn handling timing bug) that fires semi-randomly regardless of power state |
| Wedge frequency similar to pre-flip (~1 event / 20–40 min of active use) | the PM flip did not change frequency — same conclusion |
| Each event still self-settled ~10 s (matches the earlier BT basetine) | unchanged behavior apart from time-of-day |

**Conclusion recorded (Nov 2, 23:38):** power management — *both host-side*
(now disabled: adapter awake) *and* the OS-level HID stack — has been ruled
out as the wedge trigger. The defect is an in-MCU race condition, present
in every transport, in idle **and** mid-typing.

**Practical recommendation while the firmware stays unchanged:**
* **wired mode for gaming/coding sessions** — the only mode with a full
  MCU auto-cure (~1 s, invisible with the guard);
* radio (2.4G) will join "instant cure" once `resetv2/` lands;
* BT remains the *light*-mode (rare wedges but 10-s stalls + manual
  power-cycle if a storm hits) — for a game, a 10-s freeze is fatal, so
  avoid BT for reliability-critical sessions until a firmware-level
  resolution exists.

## Conclusion recorded — Nov 2, 23:38 (soak result: **host/OS PM exonerated**)

Test executed: the user flipped the TP-Link UB500 BT adapter from
`power/control=auto` (2-s autosuspend) to `on` (kept awake) and soaked the
keyboard in BT mode through an evening of *active* typing/coding/gaming
(16:00 → 23:38). Result: **wedges continued at the same rate** (9 HITs /
7 events: 19:34, 22:23 ×4, 23:20, 23:31 ×3), **several mid-typing** —
"it was happening mid typing" (user, verbatim).

Eliminated as triggers by this soak:
* the OS-side USB autosuspend of the BT adapter (was kept awake),
* the OS HID stack (no remappers; kanata disabled),
* the keyboard's own idle-sleep boundary as a *necessary* trigger
  (wedges fired **mid-typing**, not just at idle boundaries).

Which leaves the defect model as: **an internal race in the SEMICO MCU**
(key-matrix / LED / Fn-combination handling timing), firing semi-randomly
on idle *and* active use, on every transport — consistent with all
transport-differential observations so far.

**Practical recommendation (until firmware-level resolution):**
* **wired mode for gaming/coding** — the only mode with a full MCU
  auto-cure (~1 s, invisible under the guard);
* radio (2.4G) joins "instant cure" once `resetv2/` lands;
* BT remains the "light" configuration — rare wedges, but 10-s stalls and
  a manual power-cycle if a storm hits; **avoid BT for
  reliability-critical sessions** until a firmware-level fix exists.

*(original documented reasoning below, kept for the record)*

## Hypothesis consequences (original, pre-soak)

If BT wedges are (at least partly) *host-PM-induced*:
