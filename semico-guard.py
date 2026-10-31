#!/usr/bin/env python3
# semico-guard -- auto-recovery for the Redragon K552 SEMICO wedge (v2).
#
# Accuracy fix from the 22:10:22 capture: the boot keyboard report layout is
#   byte0 = report id (0x03, and a 0x02 variant was observed mid-burst),
#           byte1 = modifier bits (usually 0x00 in real bursts!), byte2 = reserved,
#           bytes 3..8 = keys
# Confirmed from the 22:10:22 / 21:57:46 / 22:17:48 idle captures:
#   rid - {2,3}, keys[] containing Esc(0x29) + Tab(0x2B) + Grave(0x35)
#   (Caps 0x39 usually rides along). Modifier bits are NOT reliably set in
#   the frame, so the trigger is keys-only (a human cannot press
#   Esc+Tab+Grave concurrently).
#   - correct byte layout and report-id filtering
#   - BlockingIOError handled as "no data, keep polling"
#   - records a short pre/post trace to the journal on each detection
#   - fires USBDEVFS_RESET on the physical port when the bundle is present
import glob
import os
import re
import select
import time

VENDOR_RE = re.compile(r'0003:1A2C:(7504|7FFF)', re.I)  # wired + 2.4G modes
USBDEVFS_RESET = 0x5514
MOD_ALWAYS = 0x00
KEY_ESC, KEY_TAB, KEY_GRAVE, KEY_CAPS = 0x29, 0x2B, 0x35, 0x39


def log(msg):
    print('semico-guard: ' + msg, flush=True)


def find_nodes():
    """return list of dict for EVERY K552-family interface 0 hidraw node."""
    out = []
    for sysnode in sorted(glob.glob('/sys/class/hidraw/hidraw*'), key=lambda p: (len(p), p)):
        real = os.path.realpath(sysnode)
        if not VENDOR_RE.search(real):
            continue
        # walk upward until we find the interface dir that has bInterfaceNumber
        cursor = real
        ifn = None
        for _ in range(5):
            cursor = os.path.dirname(cursor)
            try:
                with open(os.path.join(cursor, 'bInterfaceNumber')) as fh:
                    ifn = int(fh.read().strip())
                break
            except OSError:
                continue
        if ifn != 0:
            continue
        dev = '/dev/' + os.path.basename(sysnode)
        # climb from the interface dir to the usb parent that carries busnum/devnum
        usb_root = cursor
        usb_path = None
        for _ in range(3):
            usb_root = os.path.dirname(usb_root)
            try:
                busnum = int(open(os.path.join(usb_root, 'busnum')).read())
                devnum = int(open(os.path.join(usb_root, 'devnum')).read())
                usb_path = '/dev/bus/usb/%03d/%03d' % (busnum, devnum)
                break
            except OSError:
                continue
        out.append({'freq': dev, 'usb': usb_path})
        log('candidate: %s (usb %s)' % (dev, usb_path))
    return out


def usb_reset(path):
    import ctypes
    fd = os.open(path, os.O_RDWR)
    try:
        rc = ctypes.CDLL(None, use_errno=True).ioctl(fd, USBDEVFS_RESET, 0)
        errnum = ctypes.get_errno()
        return rc == 0, errnum
    finally:
        os.close(fd)


def analyze(frame):
    """return (wedge, mods-for-log) for a boot-keyboard frame."""
    if len(frame) < 8:
        return False, None
    rid = frame[0]
    if rid not in (0x01, 0x02, 0x03):
        return False, None
    modifiers = frame[1]
    keys = frozenset(frame[2:9]) - {0}
    # wedge: Esc+Tab+Grave held as a bundle (Caps usually too). Keys-only,
    # modifier bits unreliable in real bursts. Covered BOTH report ids (2 and 3).
    wedge = {KEY_ESC, KEY_TAB, KEY_GRAVE} <= keys
    if wedge:
        return True, modifiers
    return False, None


def main():
    trace_mode = 0
    cooldown_until = 0.0
    while True:
        nodes = find_nodes()
        if not nodes:
            time.sleep(2)
            continue
        fds = {}
        try:
            for node in nodes:
                try:
                    fd = os.open(node['freq'], os.O_RDONLY | os.O_NONBLOCK)
                    fds[fd] = node
                except OSError as ex:
                    if ex.errno == 13:
                        log('cannot open %s (EACCES) — run as root' % node['freq'])
                        return 12
                    log('skipping %s (%s)' % (node['freq'], ex))
            if not fds:
                time.sleep(2)
                continue
            poller = select.poll()
            for fd in fds:
                poller.register(fd, select.POLLIN)
            log('watching %d device(s): %s' % (len(fds), ', '.join(n['freq'] for n in fds.values())))
            active = True
            while active:
                ev = poller.poll(500)
                for fd, _ in ev:
                    node = fds[fd]
                    try:
                        data = os.read(fd, 64)
                    except BlockingIOError:
                        continue
                    except OSError:
                        active = False
                        break
                    if not data:
                        # one transport died; drop just this fd
                        poller.unregister(fd)
                        os.close(fd)
                        del fds[fd]
                        break
                    hit, mods = analyze(data)
                    if hit or trace_mode:
                        log('[%s] frame %s mods=%02x -> %s' %
                            (node['freq'], data.hex(), mods or 0, 'HIT' if hit else 'trace'))
                        if hit and time.time() - cooldown_until > 3.0:
                            cooldown_until = time.time() + 3.0
                            log('WEDGE SIGNATURE -> resetting %s' % node['usb'])
                            if node['usb']:
                                try:
                                    r_ok, r_err = usb_reset(node['usb'])
                                    log('USBDEVFS_RESET %s%s' % (
                                        'ok' if r_ok else 'FAILED errno %d' % r_err,
                                        '' if r_ok else ' -- escalate to manual unbind'))
                                except OSError as ex:
                                    log('reset error: %s' % ex)
                            else:
                                log('no usb path for reset!')
                        if trace_mode and time.time() - cooldown_until > 1.0:
                            trace_mode = 0
                if ev:
                    pass  # keep fds; actual removals surface as read errors / silent gaps
                if not fds:
                    active = False
                    log('all transports gone, rescanning')
        finally:
            for fd in list(fds):
                os.close(fd)
        time.sleep(1.5)


if __name__ == '__main__':
    main()
