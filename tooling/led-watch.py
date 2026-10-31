#!/usr/bin/env python3
# led_watch -- log CapsLock LED state flips for the K552's input nodes
# (post-21:28-replug enumeration: input225..input23x, and post-reboot too).
# Canonical home: ~/redragon-firmware/led_watch.py
import glob
import os
import re
import time

LED_NODE = re.compile(r'input2\d+::capslock')
prev_path = '/sys/class/leds/'
t0 = time.time()
prev = {}
while True:
    for l in glob.glob('/sys/class/leds/input*::capslock'):
        try:
            b = open(os.path.join(l, 'brightness')).read().strip()
        except OSError:
            continue
        if LED_NODE.search(os.path.basename(l)) and b != prev.get(l):
            print(f'{time.time()-t0:9.3f} {os.path.basename(l)} -> {b}', flush=True)
            prev[l] = b
    time.sleep(0.3)
