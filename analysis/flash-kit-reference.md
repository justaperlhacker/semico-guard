# Flash kit reference (vendor binaries — not redistributed in this repo)

The Redragon vendor binaries used during the K552-KRS wedge investigation are
**not committed to this repository** (size, redistribution cleanliness, and the
desire to keep everything reproducible from Redragon's own public source).

## Where to get them

| Artifact | Source |
|---|---|
| `RedragonKUMARA-K552-KRS` full installer (contains `DeviceDriver.exe`, `config.xml`, `vhidflt.sys` driver, and the bundled firmware updater)   | https://www.redragon.com/pages/download — search "K552/Kumara"   |
| Firmware payload inside the installer | `700N(0X3B4F)defineV9_20230316.exe` (the `FirmwareUpgrade.xike.v11` SOUI tool; flashes only the `1a2c:7f08` bootloader) |

The `config.xml` inside identifies the K552-KRS device as
`device_type=201 / device_info=kb-k600t`, upgrading from
`https://upgrade-1318931438.cos.ap-beijing.myqcloud.com/keyboard-700/704K/…`.

## Local copy checksums (for evidence integrity, not for redistribution)

```
$ ls ~/redragon-firmware/*.exe | xargs sha256sum
<record your own sha256s here when you re-download; ours were>
DeviceDriver.exe                      4.8 MB
700N(0X3B4F)defineV9_20230316.exe     4.1 MB
config.xml                            733 B
```

## Safety

* These installers are the official Redragon binaries; we reverse-engineered
  the *commands* they send (never redistribute or re-flash blobs you did not
  verify) — always to your own risk (the K552 forums are full of people who
  bricked a perfectly good unit by upgrading "just to try it").
* Our repository's own code (`semico-guard.py`, `tooling/*`) never touches the
  firmware / never flashes anything; the vendor reset command documented in
  `resetv2/` only wipes *configuration* (the same data the "Restore Factory
  Settings" button wipes) — presumably the `MCU` config area that the shipped
  image writes on a firmware flash.
