#!/usr/bin/env python3
#
# kbd-capture -- evdev keylogger for troubleshooting keyboard hardware.
#
# Captures raw input events (before any remapper like kanata grabs the
# device) and prints annotated key down/up/hold/LED lines with timestamps.
#
# Usage:
#   kbd-capture [seconds] [device-filter ...]
#     seconds         capture window, default 120
#     device-filter   substrings to match device names (default: SEMICO)
#                     e.g. kbd-capture 60 'SINO WEALTH' 'weird vendor'
#
# Examples:
#   kbd-capture                    # 120 s of the SEMICO K552
#   kbd-capture 300 blue-recover   # 5 min, match any name containing it
#
# Requires: python-evdev, and membership in the `input` group.
# Photo finish for phantom-key wedges: run it, mash the suspect keys.
#
import select
import sys
import time

import evdev

DEFAULT_FILTER = ('SEMICO',)
DEFAULT_DURATION = 120


def list_devs(filters):
    out = []
    for path in evdev.list_devices():
        try:
            d = evdev.InputDevice(path)
        except OSError:
            continue
        if any(f.lower() in d.name.lower() for f in filters):
            out.append(d)
    return out


def fmt(ev):
    try:
        return str(evdev.categorize(ev))
    except Exception:
        return f'type {ev.type} code {ev.code} val {ev.value}'


def main():
    args = sys.argv[1:]
    dur = int(args.pop(0)) if args and args[0].isdigit() else DEFAULT_DURATION
    filters = tuple(args) or DEFAULT_FILTER

    devs = list_devs(filters)
    if not devs:
        sys.exit(f'!! no devices matching {filters!r} in /dev/input')

    dests = [
        d for d in devs
        if not d.path.endswith(('_ Kanata',)) and 'kanata' not in d.name.lower()
    ]
    if len(dests) != len(devs):
        print('(-- skipping kanata virtual devices --)')
    devs = dests or devs

    t0 = time.time()
    print(f'== capturing {len(devs)} device(s) for {dur}s, filter={filters!r} ==')
    for d in devs:
        print(f'  {d.path:<22} {d.name.strip()!r} ({d.phys})')

    fdmap = {d.fd: d for d in devs}
    while time.time() - t0 < dur:
        r, _, _ = select.select(fdmap, [], [], 0.5)
        for fd in r:
            d = fdmap[fd]
            for ev in d.read():
                rel = ev.timestamp() - t0
                print(f'{rel:8.3f} {d.path:<14} {fmt(ev)}')
                sys.stdout.flush()
    print('== done ==')


if __name__ == '__main__':
    main()
