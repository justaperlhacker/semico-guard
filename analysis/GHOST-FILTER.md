# Ghost filtering as a user-side mitigation — design + proposal to Redragon

**Status (2026-11-03):** proposed-and-ready-to-build. This file documents
(a) *why* a filter daemon is a complete user-side mitigation for the SEMICO
column-0 wedge given its deterministic signature, (b) how we would build it,
(c) the follow-up proposal to Redragon support recommending they ship this
fix *inside* their own driver/firmware (a "column-0 event reject" feature).

## 1. The signature — deterministic, falsifiable, safe to filter

:: linked from `evidence-ledger.md` ("THE GHOST BUNDLE EXPLAINED"):

Every wedge emits the **matrix column 0** key set:

| row_col | key | HID usage | role in ghost frames |
|---|---|---|---|
| 0#0 | Esc | 0x29 | always |
| 1#0 | `` ` ~ `` (grave) | 0x35 | always |
| 2#0 | Tab | 0x2b | always (one transitional frame dropped it mid-burst) |
| 3#0 | CapsLock | 0x39 | usually (one transitional frame lacked it) |
| 4#0 | Shift | 0xe1 / bit 0x02 | as modifier-bit / modifier events |
| 5#0 | Ctrl | 0xe0 / bit 0x01 | as modifier-bit / modifier events |

The wedge's observable behavior = this *whole set* firing together (with
occasional decaying partial subsets mid-burst over ~10 ms). Across every
recorded wedge (10+ sessions over 2026-10-30 → 2026-11-02, all three
transports) the set never varied.

**Consequence for the *user experience*:** the icon, "keys will randomly
possess themselves" — is entirely produced by *these six inputs*. The
keyboard itself keeps working; only column 0 ghosts.

## 2. Why filtering on this signature is *safe*

A human pressing **Esc + Tab + Grave + Caps + LCtrl + LShift**
simultaneously does not occur in any real application, game or editor.
The only realistic race is user-pressed *Esc or Tab together with
Shift/Ctrl* — the standard `Ctrl+Shift+T`, `Ctrl+Shift+C` chords etc.

* Those chords use **Tab or Esc + one or both modifiers** — *without*
  Grave and *without* Caps.
* The wedge's perfect fingerprint requires **Grave AND Caps to join
  simultaneously** — which is the two keys that human chords never
  combine with this modifier-set.

Therefore a *conservative two-level* filter can be *both* invisible and
complete:

1. **Full-set shield** — the exact column-0 signature (Esc+Tab+Grave+Caps,
   ±mods) → swallow, mark the wedge window.
2. **Window suppression (10 s)** — during the window (until the last ghost
   frame + 200 ms), *any* column-0 key reported pressed is dropped
   (the wedge lasts ~10 s; dropping Esc/Tab/(grave/caps) pressed inside
   that window is a minor, tolerable loss compared to the ghost storm it
   hides). Modifiers may be re-adopted if pressed *down* again *while the
   window is closing* (users re-press Ctrl/Shift constantly, so chords
   lost for <1 s are re-completable).

## 3. How we would build `semico-filter` (user-side)

Same daemon skeleton as `semico-guard` (root, systemd, auto-reconnect,
multi-transport):

1. **Grab** every SEMICO-family evdev node (`EVIOCGRAB`; nodes are
   auto-rescanned on hotplug, same as the guard's find_nodes which already
   handles `0003:` USB and `0005:` bt/uhid).
2. **Parse** the events; maintain the column-0 key state
   (the 6 keys above).
3. **Detect** the wedge signature (full set within a short window, or the
   2-key+3-key decaying subset arriving within 200 ms).
4. **Suppress**: drop the column-0 events for the wedge window; pass
   through everything else. All suppressed groups are journaled.
5. **Replay to uinput**: the unfiltered events are forwarded through a
   virtual input device created with `uinput` so that the *rest* of the
   OS sees a normal keyboard.

The result: the *hardware wedge still happens* (the guard still resets /
the still-wedged keyboard still drops in wired mode), but the *user*
experiences **none** of its phantom-key symptoms — 10-s stalls in BT mode
shrink to "nothing happened from the user's side" plus a journaled line.

## 4. Proposal to Redragon (support follow-up)

This is the part worth writing to Redragon. The *only* way the column-0
fingerprint could exist is if the firmware has a specific column-scan
defect. If we filter such focal signatures *ourself* in the OSHI layer,
we can ask the vendor to fix the trigger *itself* in firmware. Concretely,
they could implement a **column-0 reject**:

* When the firmware detects the *exact* column-0 full-press signature
  (6 keys down at once with no physical plausibility, e.g. two keys
  > row-distance apart *plus* the two modifiers), it could skip that scan
  pass (drop the ghost frame) instead of emitting it upstream — a two-line
  debouce fix in their scanner that nobody outside their code can do.
* That fix would eliminate the user-visible phantom-key symptoms for all
  SEMICO K552/K600-family boards *without* new hardware, and without
  touching the (still broken) transport-level drop behavior.

We'll fold the exact wording into the "Upgrading The Support Email"
follow-up once `semico-filter` exists (or as a reply in the open thread —
but we've been waiting for a support answer, so a pre-emptive email
follow-up is optional).
