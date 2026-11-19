# Jukebox

A 1970s Seeburg USC2 Firestar converted to play digital music. A Raspberry Pi 5 runs
[Fruitbox v3](https://github.com/chundermike/fruitbox-v3) on a 34" ultrawide screen under the
glass. The original keypad and coin slot are kept as inputs, through a Teensy 4.1
(an Arduino-compatible board) that acts as a USB keyboard. Music comes from a Windows share; playlists made on Windows decide which songs are on
the jukebox. Audio goes from an InnoMaker HiFi DAC HAT to a bridged Blaupunkt car amplifier.

**See the [wiki](https://github.com/MTmace/Jukebox/wiki) for photos and a guided tour of the build.**

## What's in each folder

**Runs on the Pi**

| Folder | What it is | Where it goes on the Pi |
|---|---|---|
| `fruitbox/` | Fruitbox settings (`fruitbox.ini`), the launcher, screen and autostart setup | `/home/mtmace/fruitbox/` |
| `skin/` | The "Firestar Ultrawide" skin. `Firestar Ultrawide/` is the skin itself; `build_skin.py` and `status_screen.py` generate it | `Firestar Ultrawide/` goes to `/opt/fruitbox/skins/Firestar Ultrawide/` |
| `library/` | Music library: mount the Windows share, turn the playlists into categories, short strip titles, the nightly update. Start with `SETUP-GUIDE.md` | `/home/mtmace/fruitbox/` |
| `state-manager/` | Service `jukebox-state`: decides if the jukebox is starting, active, idle, in attract mode or asleep; handles the Sleep, Reboot, Rebuild Playlist and Shut Down keys | `/usr/local/bin/` and a systemd service |
| `cabinet-lights/` | Service `jukebox-lights`: the LED strips around the cabinet, driven straight from a Pi pin, following the jukebox's state | `/usr/local/bin/`, settings in `/home/mtmace/fruitbox/` |
| `status-page/` | Service `jukebox-status`: the status and control web page (http://jukebox.local) and the F24 on-screen status box | `/usr/local/bin/` and a systemd service |
| `macro-pad/` | The Koolertron macro pad's key and knob settings, and service `jukebox-bass` (the bass knob) | `/home/mtmace/fruitbox/` and a user service |

**Runs on the Teensy**

| Folder | What it is |
|---|---|
| `arduino/` | Teensy 4.1 program for the Seeburg keypad, coins, buttons and the selection number lights, plus wiring notes and a beginner guide. Uploaded from the Arduino IDE |

**Everything else**

| Folder | What it is |
|---|---|
| `3dPrints/` | Every 3D-printed part: keycaps, Pi and Teensy cases, lamp panel, button bar, splice holders, WAGO boxes, power inlet plate, status screen frame and more. Each folder has a README |
| `docs/` | Build notes: monitor mounting and volume |
| `PARTS.md` | Every part for the build and whether it is bought yet |

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
