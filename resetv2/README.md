# resetv2 — over-the-air factory reset (WIP)

> UI language note: the KUMARA app has a language selector (Chinese / English
> via `语言` dropdown in the settings dialog). Same commands either way —
> the click targets this session will be (English UI labels):
> settings gear → **Restore Factory Settings**, and the *online update*
> buttons are **Driver Update / Firmware Update** (firmware one is
> the "already latest" no-op we're NOT clicking).

**Goal:** when the K552 wedges *while in 2.4G mode*, clear the keyboard's stuck
state remotely by replaying the vendor "restore factory settings"
(`恢复出厂设置`) command to the **dongle's vendor interface**
(`/dev/hidraw12` = `1A2C:7FFF` MI_02) — the same channel Redragon's own
`DeviceDriver.exe` speaks through (and the same command that, applied over
wired USB on Oct 30, repaired the wedge state after the `Fn+Esc` disaster).

## Capture plan (tonight's session)

1. Plug the **2.4G dongle** into the Win11 VM (VMware arbitrator will offer it).
2. Boot the guest's `DeviceDriver.exe` (KUMARA app) — it supports the 2.4G
   mode explicitly (`mode value=2 desc="2.4G-TYPE_A" vid=1A2C pid=7FFF`).
3. On the **host**, start a `usbmon` tap on the keyboard's bus:
   ```
   sudo modprobe usbmon
   sudo cat /sys/kernel/debug/usb/usbmon/1u > /tmp/k552-usbmon.cap
   sudo tcpdump -r /tmp/k552-usbmon.cap ...   # filter to the dongle's bus address
   ```
   (VMware's arbitrator passes the raw URBs through the kernel's usbfs, so the
   host sees every HID write the guest makes — no guest-side Wireshark needed.)
4. In the guest: KUMARA → 系统配置 → **恢复出厂设置** → 确定.
5. Extract the HID write payload(s) (feature/output reports) that immediately
   precede and/or follow the factory-reset click. Cross-check with a
   **no-op** click (e.g. changing LED mode) so we know the byte that is
   *specific* to restore-factory (and not a generic "ping").
   *Ledger every command observed into `captured-vendor-commands.md`.*

## Implementation sketch (once the bytes are known)

* `factory-reset-over-dongle.py`:
  1. find the dongle's vendor hidraw (`1A2C:7FFF`, MI_02),
  2. `ioctl(HIDIOCSFEATURE)` or plain `write()` the payload (we'll match the
     transfer style observed in the capture — write vs SetFeature),
  3. read back the echo/ack if the keyboard sends one.
* Guard integration: an optional second stage — after a `WEDGE SIGNATURE` on
  the dongle path, if wedge frames continue beyond N frames post-reset, run
  the vendor-reset sequence (config knob; off by default until we've proven
  it doesn't make things worse).

## Bluetooth mode

Out of scope by design (see README): Redragon ships no working software
path for BT mode, and the vendor feature channel is presumed absent there.
The guard retains **BT-mode detection** (BT HID arrives via `uhid` as
`0005:1A2C:7504` — same signature logic) but only *journals* wedges; the
physical replug remains the cure for that mode.

## Open questions to answer during capture

* Does the app use HID **feature** reports (SetFeature) or **output** reports
  (interrupt OUT / `[HidDevice::Write]`)?  We saw imports both for the
  firmware flash tool — need the exact one for the settings commands.
* The 2.4G-dongle path might *batch* commands differently (single feature per
  report id) — verify against a wired capture of the same click.
* Is there a "soft reset" variant in the command vocabulary that clears the
  *key state* without wiping all data (for wedges that don't need a factory
  reset)? Guards will use the least-destructive success.
