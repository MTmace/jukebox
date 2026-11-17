# Jukebox

A 1970s Seeburg USC2 Firestar converted to play digital music. A Raspberry Pi 5 runs
[Fruitbox v3](https://github.com/chundermike/fruitbox-v3) on a 34" ultrawide screen under the
glass. The original keypad and coin slot are kept as inputs, through a Teensy 4.1
(an Arduino-compatible board) that acts as a USB keyboard. Music comes from a Windows share; playlists made on Windows decide which songs are on
the jukebox. Audio goes from an InnoMaker HiFi DAC HAT to a bridged Blaupunkt car amplifier.

**See the [wiki](https://github.com/MTmace/Jukebox/wiki) for photos and a guided tour of the build.**

## What's in each folder

| Folder | What it is | Where it goes on the Pi |
|---|---|---|
| `Fruitbox/fruitbox-setup/` | Fruitbox settings (`fruitbox.ini`), the launcher, screen and autostart setup | `/home/mtmace/fruitbox/` |
| `Fruitbox/Skins/` | The "Firestar Ultrawide" skin. `Firestar Ultrawide/` is the skin itself; `build_skin.py` and `status_screen.py` generate it | `Firestar Ultrawide/` goes to `/opt/fruitbox/skins/Firestar Ultrawide/` |
| `library/` | Music library scripts: mount the Windows share, turn the playlists into categories, short strip titles, the nightly update. Start with `SETUP-GUIDE.md` | `/home/mtmace/fruitbox/` |
| `arduino/` | Teensy 4.1 program for the Seeburg keypad, coins, buttons and selection lights, plus wiring notes and a beginner guide | Uploaded to the Teensy from the Arduino IDE |
| `hardware/` | Monitor mounting and volume notes | |
| `cabinet-lights/` | LED strips around the cabinet that follow what the jukebox is doing, driven straight from a Pi pin by the jukebox bridge | `jukebox-bridge.py` to `/usr/local/bin/`, `jukebox-bridge.ini` to `/home/mtmace/fruitbox/` |
| `button-bar/` | 3D-printable glass button bar and its optional circuit board | Printed or ordered, not on the Pi |
| `selection-lights/` | Addressable LEDs behind the 23 selection numbers: behaviour, parts, wiring and settings | Part of the Teensy program |
| `state-manager/` | One service that decides if the jukebox is starting, active, idle, in attract mode or asleep; handles the Sleep, Reboot, Rebuild Playlist and Shut Down keys | `/usr/local/bin/` and a systemd service |
| `status-page/` | The status web page (http://jukebox.local) and the on-screen status overlay | `/home/mtmace/fruitbox/status-page/` |
| `macro-pad/` | The Koolertron macro pad: key and knob settings, and the bass knob service | `/home/mtmace/fruitbox/` |
| `3dPrints/` | 3D-printable parts: keycaps, Pi and Teensy cases, power inlet plate, status screen frame and more | Printed, not on the Pi |
| `PARTS.md` | Every part for the build and whether it is bought yet | Not on the Pi |

## Notes

- Run scripts with `bash` or `python3` in front, e.g.
  `bash /home/mtmace/fruitbox/update-jukebox.sh`. Files downloaded or copied from Windows lose
  their "executable" setting. After copying `.sh` files to the Pi, run
  `chmod +x /home/mtmace/fruitbox/*.sh` once so the nightly job can start them.
- The skin folder name has a space in it, so put quotes around its path in commands:
  `sudo cp -r "/home/mtmace/Firestar Ultrawide" /opt/fruitbox/skins/`
- `.gitattributes` keeps Linux line endings on the scripts, so they still run after a trip
  through Windows.
- The skin's fonts and sounds come from Fruitbox's own stock skins. To rebuild the skin, run
  `FRUITBOX_SKINS=/opt/fruitbox/skins python3 build_skin.py` from `Fruitbox/Skins` on the Pi.

## License

MIT, see [LICENSE](LICENSE). The Seeburg name and logo, Fruitbox's fonts and sounds, and the
Bootstrap Icons keep their own owners' terms.
