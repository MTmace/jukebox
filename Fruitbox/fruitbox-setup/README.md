# Fruitbox v3 setup: genre button, autostart, attract mode

Checked against the user guide and default ini inside `fruitbox_3.02.02_arm64_portable.deb`
(the current release in github.com/chundermike/fruitbox-v3). Nothing here has been run on
the real Pi yet; the genre script was tested on a sample library.

## What Fruitbox does natively

| Ask | Native? | How |
|---|---|---|
| One button cycles a genre filter | Partly | The **MusicGroup** button (default `Right Alt`) cycles music groups and shows only that group's songs. But a group is a set of *folders*, not a genre tag, so `genre_library.py` builds one folder per genre. |
| Autostart after reboot | No | Desktop autologin plus an autostart entry (`install-autostart.sh`). |
| Toggle attract mode without reboot | Yes | The **AttractMode** button (default `'` key) toggles it live. `[attract mode] Enable` only sets the start-up state. |

## Files

- `fruitbox.ini`: the 3.02.02 default with the jukebox changes marked `# JUKEBOX`.
- `genre_library.py`: reads genre tags, builds `~/JukeboxGenres/<Genre>/...` as hard links (no extra space), and rewrites the ini's MusicPath lines.
- `genre_map.txt`: merges tag spellings into a few groups and sets the button's cycle order. Edit to taste.
- `launch-fruitbox.sh`: starts Fruitbox with this ini and restarts it after a crash (but not after a deliberate Quit).
- `send-song-codes.py`: run by the launcher before Fruitbox starts. Reads the skin's SelectButtons, numbering order and title strips, and sends the real selection codes to the keypad Teensy (e.g. `C100-108,110-118,...,270-278`), so the keypad only sends digits that make a song. Test with `python3 /home/mtmace/fruitbox/send-song-codes.py --dry-run`.
- `install-autostart.sh`: one-time Pi setup.

## Setup on the Pi

```bash
# copy this folder to the Pi, e.g. ~/jukebox-setup, then:
bash ~/jukebox-setup/install-autostart.sh
python3 /home/mtmace/fruitbox/genre_library.py --dry-run          # see the genre counts first
python3 /home/mtmace/fruitbox/genre_library.py --ini ~/fruitbox/fruitbox.ini
sudo reboot
```

Re-run `genre_library.py --ini ~/fruitbox/fruitbox.ini` after adding music.

## Genre button notes

- Each press steps: All Songs, then each genre in `genre_map.txt` order, then any other genres alphabetically, then Other. Set `MusicGroupIncludeAllSongs = No` to drop All Songs.
- A song tagged with several genres goes in the group listed first in `genre_map.txt`. Country is first, so "Pop; Country" lands in Country.
- Fewer groups means fewer presses. Genres with under 10 songs fold into Other (`--min-songs`). Fruitbox allows 30 groups at most; the script caps at 29 plus All Songs.
- Songs with no genre tag land in Other. Fix tags with mp3tag/Picard, then re-run.
- Hard links need `~/Music` and `~/JukeboxGenres` on the same ext4 drive. For music on the Windows share (or a folder of symlinks into it), use `--mode symlink`: genre folders then point straight at the real files on the share. Fruitbox following symlinks is not yet confirmed on the Pi, so check the first run; `--mode copy` is the fallback.
- If the skin's `fruitbox.cfg` has its own `MusicPath`, it overrides the ini. Remove it from the skin so the genre groups apply.
- The skin can show the current genre with `${MUSIC_GROUP}` in a `[status]` object. `genre_library.py` puts each group's song count in its label, e.g. `Country (412)` and `All Songs (1830)`, so the count shows there too.

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
- Set `SKIN="/opt/fruitbox/skins/Firestar Ultrawide/fruitbox.cfg"` in `launch-fruitbox.sh` to load the Firestar skin directly. Otherwise the chooser auto-picks the current skin after 10 seconds.
- Logs: `~/fruitbox/fruitbox.log` and `~/fruitbox/launcher.log`.
- Fruitbox refuses to start ("Can't find path") if any MusicPath folder is missing. Before each start the launcher removes MusicPath lines whose folder is gone and notes it in `launcher.log`; `genre_library.py` also only writes lines for folders that exist.

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
