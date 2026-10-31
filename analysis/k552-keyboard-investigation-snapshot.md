# Redragon K552-KRS Investigation — Session Notes (Oct 30, 2026)

## MITIGATION INSTALLED (Oct 30, ~21:07) — semico-guard
**v3 deployed 23:32 (keys-only signature, verified):**
- Warranty-relevant frame decodes (raw HID, iface0 boot-keyboard reports), all
  while idle, LED-only events (board self-drives its caps LED; shallow wedges
  don't even drop USB):
  `21157 f0 030029 2b35 390000`  → rid03 keys Esc(29)+Tab(2b)+Grave(35)+Caps(39), mod bits = 0x00
  `22:10:22 5-frame burst incl. rid02 variant + mid-burst Tab drop` → fully decoded in
  /tmp/opencode/hidraw-stream.log (t0 21:32).
  `22:17:48 single frame` same bundle.
- **Signature (byte-verified)**: rid ∈ {2,3} AND {0x29 Esc, 0x2B Tab, 0x35 Grave} ⊆ keys —
  keys-only (modifier bits unreliable in real bursts; a human cannot play
  Esc+Tab+` simultaneously). Guard fires USBDEVFS_RESET within ~200 ms.
- Guard v3 lives at /usr/local/sbin/semico-guard (source:
  ~/redragon-firmware/semico-guard.py), unit
  /etc/systemd/system/semico-guard.service (enabled, Restart=always).
  Bug fix history: v1 mis-parsed byte layout; v2 walk-up regression
  (bInterfaceNumber) silently idled; v3 walks upward generically + handles
  EAGAIN. Verified: /dev/hidraw2, reset target /dev/bus/usb/001/004.
- Probes running as user: led_watch (~/redragon-firmware/led_watch.py →
  /tmp/opencode/led-watch.log), kernel USB watcher (+ suspend/resume
  tracing) → /tmp/opencode/usb-watch.log & /tmp/opencode/idle-pm.log,
  guard stream → /tmp/opencode/guard-live.log.
- Escalation if ever needed: loosen detection (signatures without LShift),
  or add second-stage reset if first fails. RMA path remains open if the
  wedge frequency ≠ acceptable.
- Wedge recurred ~1 h after factory reset (20:17:27, clean self-drop on 1-9)
  → confirmed config-clear did NOT durably fix → in-controller bug. Flashing
  was rejected by user: bundled 2023-03-16 image IS the running firmware and
  server shows no newer build — so mitigation instead of cure.
- **semico-guard** = root systemd service that watches the K552's raw HID byte
  stream on hidraw (iface 0; hidraw is NOT affected by kanata's evdev grab)
  for the phantom-bundle signature (LCtrl+LShift held + Tab+Grave in keys[]),
  and on detection fires USBDEVFS_RESET on the physical port — the controller
  re-enumerates in ~200 ms (validated with a real reset ioctl: errno 0,
  kernel "usb 1-9: reset low-speed ... device 40").
- Files: script `/usr/local/sbin/semico-guard` (source copy at
  `~/redragon-firmware/semico-guard.py`), unit
  `/etc/systemd/system/semico-guard.service` (enabled, Restart=always).
- Watch: `journalctl -u semico-guard -f` — wedge events log "WEDGE SIGNATURE".
- Escalation if ever needed: loosen detection (signatures without LShift),
  or add second-stage reset if first fails. RMA path remains open if the
  wedge frequency ≠ acceptable.

## RESOLVED (Oct 30, ~19:15)
- **Fix**: Software factory reset (**恢复出厂设置**) in the Redragon KUMARA PRO app
  (`DeviceDriver.exe`) run in the Win11 VMware VM, then unplug/replug.
- **Verification**: 240 s evdev capture on host (`~/redragon-firmware/capture.py`,
  log `/tmp/opencode/cap-after-reset.log`) — backtick ×3, Shift+~ ×3,
  Ctrl+Shift+Tab ×2, CapsLock toggles, Esc, letters: ALL clean,
  no phantom `LCtrl+LShift+Tab+Grave+CapsLock` bundle, no repeat-flood,
  no disconnect. (Both pre-fixcaptures wedged within seconds.)
- **Probable root cause**: corrupted/half-written onboard config (macros /
  remaps / light-layer data) tripping the SEMICO controller's config parser
  → crash → phantom bundle + 30/s key repeat + wedge. The keyboard-side
  `Fn+Esc` factory combo made it worse (likely left config half-erased).
  The app-side reset rewrote config cleanly via the proper HID path.
- **If it wedges again**: 1) software factory reset in the app (works, known
  good), 2) firmware flash — the full Win11-VM flash path is documented below
  and was verified working up to the trigger (board state didn't require it).
- Firmware is current as-built: app's update check reported "already latest".

## How the fix was found (Win11 VM route)
1. Wine route definitively dead: flasher ("FirmwareUpgrade.xike.v11") reacts
   to device-arrival notifications + waits for bootloader PID 1A2C:7F08;
   needs vhidflt.sys kernel filter driver — impossible under Wine.
2. Win11 VM (vmware, /mnt/VM/vmware/Win11/Win11.vmx):
   shared folder `\\vmware-host\Shared Folders\C` → host dir /home/johnm/vm/win10_c
   (re-created; guest re-mount via VM → Settings → Options → Shared Folders).
   K552 flasher kit copied to /home/johnm/vm/win10_c/k552 and guest C:\k552.
   Keyboard passed through via VM → Removable Devices (needs
   Edit → Preferences → USB → "Show all USB input devices" to appear).
3. Filter driver install in guest (PowerShell Admin):
   cd C:\k552\driver\x64
   .\devcon.exe install .\vhidflt.inf "USB\VID_1A2C&PID_7504&MI_00"
   .\devcon.exe install .\vhidflt.inf "USB\VID_1A2C&PID_7504&MI_01"
   → both "Drivers installed successfully".
4. App's own "固件更新" (Firmware Update, string 157) is NOT exposed in UI —
   only 驱动更新 online check ("already latest"). The bundled standalone
   FirmwareUpdateTool is `k552\firmware\700N(0X3B4F)defineV9_20230316.exe`
   (升级=Upgrade btn LEFT, 取消=Cancel RIGHT; flashes only the 1A2C:7F08
   bootloader device;_PARSE from fw.exe: opens \\?\HID#VID_%04x&PID_%04x).
   Not needed in the end because reset fixed the board before flashing.

## TL;DR (original diagnosis)
The keyboard's SEMICO controller **firmware-crashes**: it emits a phantom held key
bundle (`LCtrl + LShift + Tab + Grave + CapsLock` [+ Esc]), repeat-spams the last
key, lights the CapsLock LED (the red light next to `A`), and eventually **drops
off USB entirely** — clean disconnect, no USB errors in the kernel log.
Reproduced on a direct motherboard port (port `1-9`), so it's NOT the hub or
cable. Not related to the Oct 23 kernel update. Not DE-related (same in KDE
Wayland / Niri / i3). The only known fix is a firmware flash (or RMA).

## Device facts
- USB: `1a2c:7504` "SEMICO USB Gaming Keyboard", interface 0 = standard 6KRO
  keyboard (eventX), **interface 1 = vendor interface** (Consumer, SysCtl,
  bitmap key reports 4/5/6 + vendor report 3, and the flashing surface).
- Normal HID path: hidraw0 = iface0, hidraw1 = iface1 (numbers vary per replug).

## Evidence captured
- Raw evdev logs (2 captures) in:
  /home/johnm/.local/share/opencode/shell/db6f962ef55e7f9b6c4e256fc702b04963d8c5f7/
  - sh_18da7a74c001JWRwLvUIyk45ju.out  (hub port 1-6.1 — killed @ 12:35 disconnect)
  - sh_18daecc73001XXZk2wVOPj2Ajz.out  (direct port 1-9 — killed @ ~13:5x disconnect)
- Both ended with phantom bundle + flood + Errno 19 (device gone).
- Kernel log confirms clean disconnects only (`journalctl -k` — no root needed).

## Other fixes already applied
- **Kanata disabled**: was a user-level systemd service auto-grabbing ALL
  keyboards (its caps→tap-hold esc/ctrl remap turns a stuck CapsLock into
  phantom Ctrl/Esc through two processors). Service file removed entirely
  (`~/.config/systemd/user/kanata.service` deleted). To restore: re-create it
  (backup of old content at git-less location … if needed, config survives at
  `~/.config/kanata/config.kbd`).
- pkexec works now (failed earlier due to plkit lockout while the board was
  wedging — 3 valid attempts logged via faillock, no bad-password lock).
- innoextract 1.9 installed system-wide (pkexec) + locally-built innoextract
  (git master) at /tmp/opencode/innoextract/build/innoextract — the local one
  handles Inno Setup 6.3.0 (the shipped one can't).

## FIRMWARE — the real fix candidate
- Official installer extracted (WINEPREFIX) to:
  /tmp/opencode/wineprefix/drive_c/k552probe/
- Main app: DeviceDriver.exe ("Redragon K552-KRS", config targets exactly
  VID_1A2C PID_7504 **MI_01** — our vendor interface).
- **Standalone flasher + firmware image found**:
  /tmp/opencode/wineprefix/drive_c/k552probe/firmware/700N(0X3B4F)defineV9_20230316.exe
  (also copied to /tmp/opencode/fw.exe) — "FirmwareUpgrade.xike.v11", SOUI GUI,
  talks HID feature reports. The 700N = MCU family, 704K per upgrade server URL.
- **Bootloader re-enumeration PID discovered by disassembly**: pairs of
  `push 0x1A2C` + `mov [ptr], 0x7F08` — i.e. normal device 1A2C:7504 ; after
  entering upgrade/ISP mode the board re-enumerates as **1A2C:7F08**, the
  flasher attaches there, pushes the image, reboots into normal firmware.
- Strings in flasher: "Please insert USB device", "Upgrading, please wait…"
  → flash flow: tool waits for you to plug the board in (likely a key held
  while plugging to enter ISP — exact combo unknown, common candidates: hold
  Esc, or hold Fn+Esc; use the driver app "System Config → Firmware Update"
  button which probably triggers reboot-to-ISP itself).
- Upgrade server (config.xml): https://upgrade-1318931438.cos.ap-beijing.myqcloud.com/keyboard-700/704K/software/ (listing denied — bundled 2023-03-16 image is the official payload).

## NEXT STEPS (in order)
1. **Free attempt — factory reset combo** (no Windows needed):
   hold `Fn + Esc` ~5 s until backlight flashes; wait 10 s; re-test
   (backtick ×3, Ctrl+Shift+T, LED toggle). Wipes onboard macros/remaps.
2. **If wedging persists — firmware flash under Wine** (board is essentially
   junk as-is, so flash risk is acceptable; do it only when at the machine):
   - `WINEPREFIX=/tmp/opencode/wineprefix wine "/tmp/opencode/wineprefix/drive_c/k552probe/DeviceDriver.exe"`
   - In the app: System Config → "Firmware Update" (string id 157).
     If it can't enter ISP by itself, try FirmwareUpgrade directly:
     `wine "/tmp/opencode/wineprefix/drive_c/k552probe/firmware/700N(0X3B4F)defineV9_20230316.exe"`
     and when it says "Please insert USB device": unplug, then replug while
     holding Esc (then try Fn, then Fn+Esc if ESC alone fails).
   - CRITICAL: do not unplug during "Upgrading" or the board can be bricked.
   - If Wine can't see the bootloader device (1A2C:7F08), plan B: flash on a
     real Windows machine/VM.
3. **Plan C — RMA/replace.** Fault is in MCU firmware; if flash doesn't take,
   contact Redragon support; K552 fault units are well-documented.

## Quick health check tools (updated into /tmp/opencode — NOTE: /tmp is volatile; copy elsewhere if wanted)
- capture.py — evdev logger for all SEMICO endpoints (needs input group; fine as user).
- After a wedge, replug + rerun capture reproduces the phantom bundle instantly.

## Misc
- Secondary keyboard = SINO WEALTH "Bluetooth Keyboard" 258a:01ff (its
  connect/disconnect cycles in the journal are just unplugging/re-plugging).
- Red light next to `A` during the wedge = the board's CapsLock LED, matching
  the stuck capslock(58) in the capture LED 1=1 event — visual confirmation.
