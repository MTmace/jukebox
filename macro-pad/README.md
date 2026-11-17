# Koolertron macro pad: volume, bass and lights knobs

The Koolertron 16-key, 3-knob pad is just a USB keyboard to the Pi. Each knob
sends one key when turned right, one when turned left and one when pressed.
You set those keys once on a Windows PC with Koolertron's software; the pad
remembers them, and then it plugs into the Pi with nothing installed for the
pad itself.

| Knob | Turn right | Turn left | Press | What catches it on the Pi |
|---|---|---|---|---|
| 1 Volume | `=` | `-` | Left Ctrl (mute) | Fruitbox itself (already set up) |
| 2 Bass | F17 | F18 | F19 (back to flat) | `jukebox-bass.py` (this folder) |
| 3 Lights | F14 | F15 | F13 (lights on/off) | `jukebox-lights.py` (cabinet lights) |

None of these clash with Fruitbox's keys (F1-F12, letters, digits, arrows,
Space, Backspace, Delete, Left/Right Alt, Left/Right Ctrl, `;` `'` `[` `]` `,`
`.` `/` Tab Esc SysRq) or with Pause (screens off).

**If the Koolertron software has no F13-F19:** use Home / End for bass and
Page Up / Page Down for the lights, with Scroll Lock as the lights press. The
Pi listens for those too. Leave the bass press empty in that case.

## 1. Program the pad (Windows)

1. Plug the pad into the PC and open the Koolertron software.
2. Click knob 1. Set **turn right** = `=`, **turn left** = `-`, **press** = Left Ctrl.
3. Knob 2: right = F17, left = F18, press = F19.
4. Knob 3: right = F14, left = F15, press = F13.
5. Click the button that writes/downloads the settings to the pad, then unplug it.

Test on the PC first: open Notepad and turn knob 1, you should see `===` and `---`.

## 2. Bass on the Pi

Copy `jukebox-bass.py`, `jukebox-bass.conf`, `jukebox-bass.service` and
`install-bass.sh` into `/home/mtmace/fruitbox/`, then over SSH (not with sudo):

```
bash /home/mtmace/fruitbox/install-bass.sh
sudo reboot
```

What it does: adds a sound output called "Jukebox Bass" in front of the DAC
and makes it the Pi's default, so Fruitbox plays through it. It boosts or cuts
everything below about 100 Hz, 2 dB per click, from -12 to +12 dB. The level
is saved and comes back after a reboot.

Test without the pad: `python3 /home/mtmace/fruitbox/jukebox-bass.py --set 8`
(lots of bass), then `--set 0` (flat). Log: `journalctl --user -u jukebox-bass -f`.

If you followed the earlier alsaequal steps (`/etc/asound.conf`), the installer
moves that file aside: it sent sound around PipeWire straight to the DAC, which
would bypass this knob and stop the sound-reactive cabinet lights hearing the music.

Big bass boosts at a high Fruitbox volume can distort. At the normal volume
(around 30) there is plenty of room.

## 3. Lights

Nothing new: the cabinet lights service (`cabinet-lights/jukebox-lights.py`)
already dims on F14/F15 and switches on/off with F13. It works once it
is installed on the Pi (see `cabinet-lights/README.md`).

## 4. Reboot, Rebuild Playlist, Shut Down and Sleep keys

Program the pad keys: Reboot = **F20**, Rebuild Playlist = **F21**, Shut Down = **F22**,
Sleep = **Pause**. Each needs **two presses within 5 seconds**, so a bumped key does nothing.
They are handled by the state manager (`state-manager/`, service jukebox-state), which
replaced the old jukebox-keys service on 2026-11-14.

| Key | Two presses do |
|---|---|
| F20 Reboot | restarts the Pi |
| F21 Rebuild Playlist | runs `update-jukebox.sh` (rescans the music), then restarts the Pi. Takes a minute or two before the restart. |
| F22 Shut Down | safe power-off. Wait until the screens and lights go dark, then switch the power off. |
| Pause Sleep | screens off and the cabinet lights to their sleep look. Any key wakes it. See `state-manager/README.md`. |

## Undo

```
systemctl --user disable --now jukebox-bass
rm ~/.config/pipewire/pipewire.conf.d/jukebox-bass.conf
sudo reboot
```
