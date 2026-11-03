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

## Hypothesis consequences

If BT wedges are (at least partly) *host-PM-induced*:

| Observation after the PM flip | Interpretation |
|---|---|
| BT wedges **stop** or frequency drops sharply | the adapter's 2 s autosuspend was a *major contributor*; keep BT PM off forever (udev rule does this), wedges that remain are the MCU's own idle race |
| BT wedges **unchanged** in rate and shape | host PM is *exonerated* for BT; the wedge trigger sits inside the keyboard's internal idle path (battery-powered MCU logic), which then feeds the keepalive-experiment theory directly |
| BT wedges reduce but persist | both layers contribute (host PM and keyboard idle logic); the LED-keepalive experiment should then target the remainder |

## Conclusion recorded

A BT-mode daily soak with this flipped will answer the question with data —
the guard journals every wedge anyway (with transport stamps), and
`btmon` maintains a full HCI trace in `/tmp/opencode/bti.btmon` for the
link-drop particulars (e.g., whether a wedge produces an actual
*HCI disconnection event*).
