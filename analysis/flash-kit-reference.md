# Flash kit reference (vendor binaries — not redistributed in this repo)

The Redragon vendor binaries used during the K552-KRS wedge investigation are
**not committed to this repository** (size, redistribution cleanliness, and the
desire to keep everything reproducible from Redragon's own public source).

## Where to get them — verified 2026-11-02 against the official portals

| Artifact | Where it lives | Status |
|---|---|---|
| **K552-KRS driver installer** (`Redragon_K552-KRS_Mechanical_Gaming_Keyboard_setup_1.0.4.6.exe`) | official Download page: https://www.redragon.com/pages/software-download → "Keyboard Software" → **K552-KRS** (shopify-hosted EXE) | ✅ published — this is the same installer we extracted (`DeviceDriver.exe` + `vhidflt.sys` + the bundled `700N(0X3B4F)defineV9_20230316.exe` FirmwareUpdateTool) |
| **K552-KRS standalone firmware download** | **none** — unlike some sister models (e.g. K719RGB-PRO, K716 get explicit "(Firmware)" kits on regional portals like redragon.es), the K552-KRS ships **no separate firmware item** on any official portal we checked (US/EU/zone/BR) | ❌ the *only* update channel for this model is the **app's OTA** (`Driver/Firmware Update` in the KUMARA app → the upgrade server reported "already latest") |
| Regional vendor portals | redragonshop.com/pages/software · redragonzone.com/software.html (JS-driven) · redragon.es "drivers & downloads" (has a **Firmware category** for *other* models) · redragon.com.br/downloads | worth re-checking manually if our RMA ticket asks for a newer build |
| Firmware-update tool when the vendor sends them | precedent: Redragon support replies with direct links on request (documented in the K630 thread, r/MechanicalKeyboards) | 📧 support@redragon.com |

## The upgrade server (from `config.xml` / kb-k600t layout — probed 2026-11-02)

```
https://upgrade-1318931438.cos.ap-beijing.myqcloud.com/keyboard-700/704K/software/
https://upgrade-1318931438.cos.ap-beijing.myqcloud.com/keyboard-700/704K/firmware/
```
Direct GETs for listing or manifest names return **404** — objects are
gated and delivered only to the app in its own protocol (and only for
`device_type=201 / device_info=kb-k600t` — i.e., the K552-KRS).

```
$ ls ~/redragon-firmware/*.exe | xargs sha256sum   (record your own copies here)
DeviceDriver.exe (${size} MB)
700N(0X3B4F)defineV9_20230316.exe (${size} MB)
```

## Safety

* The installer above is the official Redragon binary; our repo reverses
  *commands*, not blobs, and never redistributes or blind-flashes vendor
  payloads.
* The KUMARA app's "Firmware Update" OTA says "already latest" — that is the
  honest official answer: no newer `keyboard-700/704K` build is published as
  of 2026-11-02. The bug is *not* fixed by anything the vendor currently
  ships for this SKU.
* For the future: re-running the KUMARA app's update check after enough time
  is what would surface a new `FirmwareUpdateTool-<ver>.exe` — but there is
  no public changelog to expect one from; the upgrade server gates the
  objects, so nothing about them is inspectable externally.
