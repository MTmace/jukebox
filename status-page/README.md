# Jukebox status page

A troubleshooting page that shows everything the jukebox is set to, in one place.

- **On your PC or phone:** open **http://jukebox.local** (or `http://<the Pi's IP>`).
  It refreshes every 5 seconds. Read only: nothing on it changes the jukebox.
- **On the jukebox itself:** press **F24** on the macro pad. A status box covers the
  main screen until you press F24 again. Fruitbox keeps playing and the
  keypad keeps working underneath.

## What it shows

| Section | Values |
|---|---|
| Things to check | Plain-English warnings: Fruitbox not running or frozen, muted, paused, DAC missing, bass output not in use, lights switched off, a service stopped, music share not connected, Pi hot or short of power, USB drive full, screens asleep, no network |
| Playing | Jukebox state (with a link to a page explaining each state), Song and artist, genre/playlist, songs in queue, attract mode, credits, songs in library |
| Sound | Fruitbox volume (0 to MaxVolume) and mute, volume step and start volume from fruitbox.ini, bass now (dB) with its start level and range, DAC Digital level, the Pi's output volume, which sound output is in use |
| Lights | On/off, brightness, theme, favourites 1/2/3, which look the lights show (from the jukebox state), idle, sleep and white levels; link to a Light themes page (what each theme shows in each state, read from the installed jukebox-bridge.ini comments) |
| Screens | Skin, each screen's size, position and rotation, screens on or asleep |
| Network | Name, IP address, WiFi name and signal, page address |
| Pi | Temperature, power/heat warnings (under-voltage), 5 V supply voltage, uptime, free space |
| Services | jukebox-bridge, jukebox-state, jukebox-status, jukebox-bass, Fruitbox: running, starts at boot, and the installed version (the script's VERSION line, file, install date, and an id matching `git hash-object` of the repo file); Fruitbox package version |
| Music and devices | Music share, playlist folders, keypad Teensy, LED pins, USB devices |
| Settings files | fruitbox.ini, jukebox-bridge.ini, config.txt, cmdline.txt (click to open) |
| Recent log lines | launcher.log, fruitbox.log, and each service's log (click to open) |

Volume, song, genre and skin only exist inside Fruitbox. The installer adds one hidden
status box to the end of the skin's `fruitbox.cfg` (like the one the lights already use),
so Fruitbox writes them to `/dev/shm/jukebox_fruitbox.txt` once a second. The skin file is
backed up first as `fruitbox.cfg.before-status`; nothing else in it changes.

## Install

1. Program the spare macro pad key (top row, 3rd from the left) as **F24**. Its cap is `3dPrints/Keycaps/top-half/keycap_top_info-lg.3mf`; the pad map PDFs show it as Status Screen.
   (Koolertron software on the PC, then write it to the pad).
2. Copy this folder to the Pi (it lands in `/home/mtmace/fruitbox/status-page/`). From PowerShell on the PC:

   ```
   scp -r C:\Users\MTmace\Documents\Jukebox\status-page mtmace@Jukebox:/home/mtmace/fruitbox/
   ```

3. On the Pi (ssh mtmace@Jukebox):

   ```
   sudo bash /home/mtmace/fruitbox/status-page/install-status.sh
   sudo reboot
   ```

4. Open http://jukebox.local on the PC.

Quick check over SSH without a browser:
`python3 /usr/local/bin/jukebox-status.py --print`

Log: `journalctl -u jukebox-status -f`

Remove: `sudo bash /home/mtmace/fruitbox/status-page/install-status.sh off`

## Settings

At the top of the scripts (in `/usr/local/bin/` once installed):

- `jukebox-status.py`: `SHOW_KEYS` (the key that shows the box, F24), `PORTS` (80, then 8080 if 80 is taken).
- `jukebox-status-overlay.py`: `SHOW_SECONDS` (0 = stays up until the key is pressed again), `SCREEN` (`primary` = the main screen; `HDMI-2` = the bar screen), size in %.

After a change: `sudo systemctl restart jukebox-status`.

## Files

| File | Goes to |
|---|---|
| `jukebox-status.py` | `/usr/local/bin/` (web page + F24 key) |
| `jukebox-status-overlay.py` | `/usr/local/bin/` (the on-screen box) |
| `jukebox-status.service` | `/etc/systemd/system/` (runs as mtmace, starts at boot) |
| `jukebox_status.txt` | the skin folder (what Fruitbox writes out) |
| `install-status.sh` | runs from `/home/mtmace/fruitbox/status-page/` |

If the skin is rebuilt with `Fruitbox/Skins/build_skin.py`, the hidden box is already included.

## Normal ranges

Values are green when normal, amber when worth a look, red when something is wrong.

| Value | Green | Amber | Red |
|---|---|---|---|
| Pi temperature | under 70 °C | 70-80 °C | 80 °C and up (the Pi slows itself down at 80-85) |
| Power / heat warnings | none | "since boot" only (happened earlier) | anything "NOW" |
| 5 V supply | 4.9 V and up | 4.75-4.9 V | under 4.75 V |
| WiFi signal | -30 to -67 dBm | -67 to -75 dBm | weaker than -75 dBm |
| Ping to router / music PC | under 20 ms, 0% lost | 20-100 ms or some lost | over 100 ms, 25% lost, or no reply |
| CPU use | under 60% | 60-85% | over 85% |
| Memory, USB drive | under 80% used | 80-90% | over 90% |
| Pi output volume | 100% | anything else | |
| Sound output | Jukebox Bass | anything else (bass knob won't work) | |

Ping is a good WiFi health check: the time is how long the router (or the music PC)
takes to answer, and "lost" is how many of 4 tries got no answer. Lost pings or times
over about 100 ms are what make music from the share stutter.

## Versions

Each service script has a `VERSION = "1.0"` line near the top. Bump it on every
change (1.0 -> 1.1), so the Services section shows which one the Pi is running.
A script without the line shows "no version"; the id still identifies the exact file.

## Settings come from the installed files

The page has no copies of settings of its own. Volume figures come from
fruitbox.ini; the bass start level and range from the `DEFAULT_DB`, `MIN_DB`,
`MAX_DB` lines of the installed jukebox-bass.py; the times on the states page
(`ACTIVE_SECONDS`, `SLEEP_MINUTES`, `CONFIRM_SECONDS`) from the installed
jukebox-state.py; light levels and themes from jukebox-bridge.ini. Change the
file, restart that service, and the page follows (a "?" means it couldn't read it).

## Control page (1.4)

http://jukebox.local/control (the "control" link at the top of the status page).
The status page itself stays read-only; every action is on this separate page.
Each section has dropdowns and a Go button.

- **Jukebox state** (one dropdown): Wake up, Sleep, Attract on / off, Reboot, Rebuild playlists,
  Shut down. These go to the state manager (needs jukebox-state 1.4), which does
  exactly what the keys do. The buttons and which ones ask "are you sure?" come
  from `WEB_REQUESTS` / `WEB_CONFIRM` in the installed jukebox-state.py.
- **Services** (service dropdown + action dropdown): Start / Restart / Stop for every `jukebox-*.service` installed
  (system ones in /etc/systemd/system, user ones in ~/.config/systemd/user).
  Stop asks "are you sure?" first. The status page itself can only be restarted.

No PIN: anyone on the home network can use it. Buttons send a form, so a link,
a bookmark or a page refresh never presses one. The installer adds
/etc/sudoers.d/jukebox-status so the page may start / stop / restart only the
jukebox services installed at that time; run the installer again after adding a
new service.
