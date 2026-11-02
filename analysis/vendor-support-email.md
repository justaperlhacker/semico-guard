Subject: K552-KRS (wireless TKL, tri-mode) — reproducible phantom-key firmware wedge (byte-level evidence attached)

Dear Redragon support team,

I own a Redragon K552-KRS (wireless TKL tri-mode, Type-C/BT 5.0/2.4G; S/N per
receipt available on request), part # 1295768 on your store
(redragon.com/products/redragon-k552-krs-tkl-mechanical-gaming-keyboard).

This report documents a reproducible firmware fault in its SEMICO USB
controller, and my attached evidence is complete down to the byte. I would be
glad to share all files/traces, and I would like to know whether a newer
firmware for this keyboard exists for my unit.

## Symptom

The keyboard randomly enters a "wedge" state:

* the raw USB HID stream floods with a phantom held-key bundle
  (Esc + Tab + Grave + CapsLock, plus Ctrl/Shift modifier traffic — equivalent
  to LCtrl+LShift held while ESC+TAB+` pressed simultaneously),
* the CapsLock LED lights by itself (no host involvement),
* repeat-gapping at ~30 strokes/s on the last key,
* and then the board *drops off the USB bus* (wired mode) or floods until
  reset (2.4G mode).

It happens **while the keyboard is completely idle** (no user input), on a
clean Linux system, on a direct motherboard port, and on all three connection
modes: wired, 2.4G receiver, Bluetooth. Nothing external is involved.

## Byte-level evidence (raw HID stream, boot-keyboard reports)

Observed ghost frames (idle wedges, 2026-10-30 through 2026-11-02):

    0300292b35000000        wired (rid3, mods=00, keys=ESC Tab `)
    0300292b35390000        wired (rid3 ... + Caps)
    0200292b35390000        rid2 variant of the same bundle
    0300293539000000        mid-burst (Tab released)
    010300292b3539...0000   Bluetooth (same bundle, rid3 inside a BT report)

(Full ledger with 10+ timestamped captures across wired/2.4G/BT, analyses and
supporting files: https://github.com/justaperlhacker/semico-guard — see
analysis/evidence-ledger.md and analysis/MASTER-ISSUE.md.)

## Workaround attempts that did NOT hold

* app "Restore Factory Settings" (config rewrite through your own
  `DeviceDriver.exe`, device mapped as kb-k600t / device_type 201): the wedge
  state returned within one hour;
* the driver bundle's own `vhidflt.sys` filter and the standalone
  `700N(0X3B4F)defineV9_20230316.exe` firmware-update tool: the app's
  *Firmware Update* reports "already running on the latest version";
* OS-side USB power management (disabled at the port level): eliminates the
  OS as a trigger — the fault is on the keyboard MCU side.

## The workaround that DOES work

Because the MCU reloads when its port is reset, my `semico-guard` tool
(systemd daemon, attached as reference) detects the ghost-bundle signature on
raw hidraw and issues `USBDEVFS_RESET` on the offending port. Recovery is
~0.2-1.0 s in **wired** mode. In 2.4G/Bluetooth modes the receiver can only be
re-synced (the MCU is battery powered) and the stuck state survives longer.

## My requests

1. Is there a firmware update for the K552-KRS newer than the image published
   inside the 1.0.4.6 driver package (defineV9 2023-03-16)? If yes, please
   send the download link of the update tool.
2. Could you please confirm whether this wedge is a known issue for the
   SEMICO `keyboard-700/704K` family (device_type 201), and if a fixed build
   exists.
3. If the issue is confirmed and unfixed, I'd like to open a warranty case
   for the replacement of the unit — my receipt is available. I can also
   supply the full trace files (usbmon packet logs of the flasher/ISP session
   and journals of every wedge event with timestamps).

Serial number / purchase proof will follow upon reply. Thank you for the
great hardware — this is purely a firmware-crash report and I am happy to work
with your engineering team to nail it down (forum thread cross-links and a
public repository with the reproducible logs are ready).

Best regards,
<your name>
<country/timezone>
<your support email>
