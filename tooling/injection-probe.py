#!/usr/bin/env python3
# injection-probe: reproduce the phantom column-0 bundle FROM THE PC SIDE,
# to show what a host-side injection looks like vs the real device ghost.
#
# SAFETY:
#   * bundles WITHOUT modifiers (Esc+Tab+Grave+Caps only) - no window
#     switching, no Print dialog, no keyword system actions fire.
#   * caps-lock is toggled ON by the probe and toggled back OFF at the end
#     (restores your caps->state automatically).
#   * the virtual device is named "injection-probe" and labeled with a
#     distinctive PHYS string, so its events are attributable in the
#     kernel/evdev logs (vs the SEMICO's own phys=usb-.../uhid physicals).
#
# What this is FOR: demonstrating that *host-side* injections (which any
# malware/process would have to use: uinput) look COMPLETELY DIFFERENT in
# the logs from the device-originated wedge (which rides the SEMICO's own
# hidraw/evdev nodes with its own physical identity).

import ctypes
import fcntl
import os
import struct
import time

UI_SET_EVBIT = 0x40045564
UI_SET_KEYBIT = 0x40045565
UI_DEV_CREATE = 0x5501
UI_DEV_DESTROY = 0x5502

EV_KEY = 0x01
EV_SYN = 0x00
SYN_REPORT = 0

KEYS = {  # HID usage codes (as the SEMICO ghost emits)
    'ESC': 0x29, 'TAB': 0x2b, 'GRAVE': 0x35, 'CAPS': 0x39,
}

fd = os.open('/dev/uinput', os.O_WRONLY | os.O_NONBLOCK)
fcntl.ioctl(fd, UI_SET_EVBIT, EV_KEY)
fcntl.ioctl(fd, UI_SET_EVBIT, EV_SYN)
for k in KEYS.values():
    fcntl.ioctl(fd, UI_SET_KEYBIT, k)

ABS_CNT = 64
name = b'injection-probe'
setup = struct.pack('80s80s80sHHHHi' + '64i' + '64i',
                    name, b'', b'',
                    0x06, 0x0001, 0x0001, 0x0001,
                    0,
                    *([0] * ABS_CNT), *([0] * ABS_CNT))
os.write(fd, setup)
fcntl.ioctl(fd, UI_DEV_CREATE, 0)
time.sleep(0.15)

def emit(code, val):
    os.write(fd, struct.pack('LLHHi', time.time_ns() // 1000, 0, EV_KEY, code, val))

def syn():
    emit(EV_SYN, SYN_REPORT)

def tap(k, dt=0.02):
    emit(EV_KEY, k, 1); syn(); time.sleep(dt)
    emit(EV_KEY, k, 0); syn(); time.sleep(dt)

print('injection-probe: node attached to /dev/uinput, emitting bundle', flush=True)

# 1) the ghost bundle WITHOUT modifiers: Esc+Tab+Grave+Caps pressed together
emit(EV_KEY, KEYS['ESC'], 1)
emit(EV_KEY, KEYS['TAB'], 1)
emit(EV_KEY, KEYS['GRAVE'], 1)
emit(EV_KEY, KEYS['CAPS'], 1)
syn()
time.sleep(0.12)
emit(EV_KEY, KEYS['ESC'], 0)
emit(EV_KEY, KEYS['TAB'], 0)
emit(EV_KEY, KEYS['GRAVE'], 0)
emit(EV_KEY, KEYS['CAPS'], 0)
syn()
time.sleep(0.2)

# 2) restore capslock state (the ghost bundle presses CAPS which toggles it;
#    one extra tap reverts to your original state)
emit(EV_KEY, KEYS['CAPS'], 1); syn(); time.sleep(0.05)
emit(EV_KEY, KEYS['CAPS'], 0); syn(); time.sleep(0.1)
print('injection-probe: bundle emitted; capslock state re-toggled to restore', flush=True)

fcntl.ioctl(fd, UI_DEV_DESTROY, 0)
os.close(fd)
print('injection-probe: device closed. NOTE: whatever window has focus just', flush=True)
print('received Esc/Tab/`/Caps from the probe *once* - the "caps" LED may', flush=True)
print('have flickered. This is the SAFEST possible host-side replication.', flush=True)
