#!/usr/bin/env python3
"""Capture evdev events from all SEMICO (1A2C:7504) input devices."""
import sys, evdev, time

def semico_devices():
    devs = []
    for path in evdev.list_devices():
        try:
            d = evdev.InputDevice(path)
        except OSError:
            continue
        if 'SEMICO' in d.name or 'USB Gaming Keyboard' in d.name:
            devs.append(d)
    return devs

def main():
    dur = int(sys.argv[1]) if len(sys.argv) > 1 else 120
    t0 = time.time()
    devs = semico_devices()
    if not devs:
        print('!! no SEMICO devices found'); return
    print(f'== capturing {len(devs)} device(s) for {dur}s ==')
    for d in devs:
        print(f'  [{d.path}] {d.name!r}')
    print()
    for d in devs:
        print(f'CAP start: {d.path} {d.name!r} phys={d.phys}')
    fdmap = {d.fd: d for d in devs}
    import select
    while time.time() - t0 < dur:
        r, _, _ = select.select(fdmap.keys(), [], [], 0.5)
        for fd in r:
            d = fdmap[fd]
            for ev in d.read():
                k = getattr(evdev.ecodes, 'KEY', None)
                try:
                    name = evdev.categorize(ev)
                    desc = str(name)
                except Exception:
                    desc = f'{ev.type} {ev.code} {ev.value}'
                t = ev.timestamp() - t0
                print(f'{t:8.3f} {d.path:<14} {desc}')
                sys.stdout.flush()
    print('== capture window ended ==')

main()
