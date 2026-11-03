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

## Workaround actually deployed (2026-11-03): app-level chord armor (kitty)

Live evidence (Nov 3, 00:34 storm): the ghost arrives in BT mode with
modifier bits *held* (LCtrl+LShift = 0x03) inside the ghost frame, plus a
TAB (and an ENTER in one escalated frame). That chord lands on focused
apps. In the reporter's own kitty config, the app-level chord
`ctrl+shift+t` was mapped to `new_tab` — so the ghost spawned real kitty
tabs and help windows.

MITIGATION applied: app-level "no-op the ghost chords" (kitty.conf):

    map ctrl+shift+tab no_op
    map ctrl+shift+grave no_op
    # (ctrl+shift+escape was already discard_event'd by the reporter)

This kills the kitty-window spawns *specifically*, zero flashing. Backups
saved (`kitty.conf.semico-bak`). Same treatment is recommended for any
app with chords composed ONLY of ghost-bundle keys (Tab/Esc/Enter/Grave/Caps
+ Ctrl and/or Shift) that should be ignored.

(In niri, global binds all require Mod=Super — never part of the ghost — so
the compositor-level shortcuts were already safe. Other apps (editor/IDE,
browsers) can get the same treatment per-config: remap any chord that uses
only ghost-bundle keys with an ALT-based variant, since Alt is never in the
ghost payload.)

This MEASURABLY reduces the wedge's real-world impact in BT mode while
resetv2 (over-the-air factory reset) and the custom-firmware rungs wait.
It does not fix the underlying defect — the guard still journals
everything, the wedge still fires — but the hideous symptoms become largely
invisible.


## Complete chord table for kitty (2026-11-03, after the escape-question from
## the reporter: "what about tab?")

| ghost chord at the app level | kitty disposition | status |
|---|---|---|
| `ctrl+shift+escape` | reporter had *already* no-op'd it (`discard_event`) — well designed | ✅ safe |
| `ctrl+shift+t` | was `new_tab` | ⛔ **never reachable** (contains `T`/0x17 — no letter byte has ever appeared in a ghost frame) → the temporary no_op was **reverted**, `new_tab` restored |
| `ctrl+shift+tab` | **not a kitty default** — safe to no_op | ✅ no-op added |
| `ctrl+shift+enter` | not a kitty default (verified in kitty 0.49.2) | ⚠️ added speculatively on the single Enter escalation, then **removed** — it defended nothing. Re-add only if a future capture shows Enter becoming routine |
| `ctrl+shift+grave` | not a kitty default | ✅ no-op added |
| plain `Tab` / `Esc` / `Grave` / `Caps` **without modifiers** | kitty passes them to the running program as normal keys — *cannot* be globally no-op'd without breaking typing | ⚙️ handled only by the filter-daemon design (drop column-0 keys during wedge-suppression windows) |
| `Caps` state key | kernel handles CapsLock state (LED + kbd lock) — kitty cannot no-op it | 🧩 wedge self-clears (press Caps once manually to undo a false toggle) |

## Correction of record
An earlier note suggested the phantom kitty tabs came via
`ctrl+shift+t → new_tab`. That hypothesis is **withdrawn**: the recorded
ghost frames contain no letter-T (0x17) byte — the actual chord reaching
focused kitty windows with the ghost set was *ctrl+shift+tab* (modifiers +
the Tab key), for which kitty has **no default action**. The no-op approach
above closes every ghost chord that *could* exist, while the plain-key
members of the column remain the filter daemon's domain (they are typing
keys with legit uses).

## Correction of record #2 (2026-11-03, later same day)

Two items from the first armor pass are **withdrawn**, after the reporter
pointed out (a) `Ctrl+Alt+T` is their KDE *konsole launcher* global shortcut
and (b) `ctrl+shift+enter` had no evidentiary basis:

1. **`map ctrl+alt+t new_tab` — removed.** It collided with a real global
   shortcut (KWin grabs it before the app even sees it), and it was
   unnecessary: the ghost never emits Alt.
2. **`map ctrl+shift+t no_op` — removed, `new_tab` restored.** The ghost
   cannot emit any letter byte, so the chord was never reachable. The no_op
   merely destroyed a working shortcut.
3. **`map ctrl+shift+enter no_op` — removed** after verifying it is not a
   kitty default binding in 0.49.2 (it was pure speculation layered on the
   one escalated frame).

**Final deployed armor = exactly the ghost's reachable chord set, nothing more:**

| Chord | Reachable from ghost bytes? | Disposition |
|---|---|---|
| `ctrl+shift+tab` | yes (mods 0x03 + `0x2B`) | `no_op` |
| `ctrl+shift+grave` | yes (mods 0x03 + `0x35`) | `no_op` |
| `ctrl+shift+escape` | yes (mods 0x03 + `0x29`) | `discard_event` (pre-existing) |
| `ctrl+tab`, `shift+tab`, `ctrl+grave`, … | yes (single-modifier variants) | not bound in kitty → nothing to do |
| `ctrl+shift+t`, `Ctrl+Alt+T`, any letter chord | **no** | untouched |

Principle worth keeping: **armor only the chords the firmware can physically
emit.** Every extra no_op is a real shortcut you are silently donating to a
bug. The reachable set is small and closed: `{LCtrl, LCtrl+LShift} ×
{Esc, Tab, Grave, Caps}` (+ `Enter` on escalation).
