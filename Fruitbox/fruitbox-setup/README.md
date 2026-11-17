# Fruitbox v3 setup: settings, launcher, autostart, screens

Fruitbox's settings for this jukebox and the scripts that start it. Everything here goes in
`/home/mtmace/fruitbox/` on the Pi.

## Files

- `fruitbox.ini`: Fruitbox's settings (buttons, credits, attract mode), the 3.02.02 default
  with the jukebox changes marked `# JUKEBOX`. Its `MusicPath` lines are written by
  `library/playlist_library.py`, one per playlist category, so don't edit those by hand.
- `launch-fruitbox.sh`: starts Fruitbox with this ini and restarts it after a crash (but not
  after a deliberate Quit). Run at login.
- `send-song-codes.py`: run by the launcher before Fruitbox starts. Reads the skin's
  SelectButtons, numbering order and title strips, and sends the real selection codes to the
  keypad Teensy (e.g. `C100-108,110-118,...,270-278`), so the keypad only sends digits that
  make a song. Test with `python3 /home/mtmace/fruitbox/send-song-codes.py --dry-run`.
- `setup-screens.sh`: one-time setup of the two-screen layout (see the file).
- `install-autostart.sh`: one-time Pi setup: desktop autologin, no screen blanking, Fruitbox
  at login.

## Setup on the Pi

```bash
# copy this folder to the Pi, e.g. ~/jukebox-setup/fruitbox, then:
bash ~/jukebox-setup/fruitbox/install-autostart.sh
```

Then set up the music library (`library/SETUP-GUIDE.md`) and reboot.

## Buttons Fruitbox handles itself

| Jukebox control | Fruitbox button | Key the Teensy sends |
|---|---|---|
| Genre (playlist category) | MusicGroup | Right Alt |
| Attract on/off | AttractMode | `'` |
| Selection digits | Select0..9 | `0`..`9` |
| Coin slot | Coin1 | F1 |

Any key can be remapped in `[buttons]` or from the on-screen Menu (`Tab`) > Controls.

## Attract mode notes

- Plain toggle out of the box. If the skin's `[general]` lists genres, e.g.
  `AttractModeGenre = Rock & Roll` and `AttractModeGenre = Soul`, the same button instead cycles Off, then each genre, then Any. `${ATTRACT_MODE_GENRE}` shows the current one.
- Fade and timing: `[attract mode]` FadeIn, FadeOut, FadeInPosition, FadeOutPosition, Interval, MaxVolume.

## Keys the keypad controller (Teensy 4.1) should send

| Jukebox control | Fruitbox button | Arduino `Keyboard.h` |
|---|---|---|
| Genre | MusicGroup | `Keyboard.write(KEY_RIGHT_ALT)` |
| Attract on/off | AttractMode | `Keyboard.write('\'')` |
| Selection letters / digits | SelectA..Z, Select0..9 | `'A'`..`'Z'`, `'0'`..`'9'` |
| Coin slot | Coin1 | `Keyboard.write(KEY_F1)` |

Any key can be remapped in `[buttons]` or from the on-screen Menu (`Tab`) > Controls.

## Autostart notes

- Uses `~/.config/autostart/fruitbox.desktop`, which Raspberry Pi OS runs on both labwc (Wayland) and X11 desktops.
- Esc (Quit) drops to the desktop and stays there; reboot to bring the jukebox back. Remove `fruitbox.desktop` to stop autostart.
- `SKIN=` in `launch-fruitbox.sh` loads the Firestar skin directly. Set it to `""` to get the skin chooser instead.
- Logs: `~/fruitbox/fruitbox.log` and `~/fruitbox/launcher.log`.
- Fruitbox refuses to start ("Can't find path") if any MusicPath folder is missing. Before each start the launcher removes MusicPath lines whose folder is gone and notes it in `launcher.log`.

## Screens off (sleep)

The state manager (`state-manager/`, service jukebox-state) handles sleep: after
10 minutes idle, or Pause pressed twice, the screens go off and the music stops.
Any keypad or macro pad press wakes it. The old screen-sleep.sh, its nightly cron
and the xbindkeys Pause key were retired on 2026-11-16 (see state-manager/README.md).

## Desktop menu bar over Fruitbox

The Pi's desktop menu bar can end up on top of Fruitbox's header after a reboot
(it depends on which starts first). Set it to hide itself: in
`/home/mtmace/.config/lxpanel-pi/panels/panel` set `autohide=1` and
`heightwhenhidden=0`, then run `DISPLAY=:0 lxpanelctl-pi restart`.
Undo: put `autohide=0` back (the jukebox keeps a backup as `panel.bak`).
