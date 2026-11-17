# Jukebox state manager (step 1)

One program, `jukebox-state`, decides which state the jukebox is in and writes
it to `/dev/shm/jukebox_mode`:

| State | When |
| --- | --- |
| starting | from boot until Fruitbox is up |
| idle | no song and no key, knob or coin for 60 s |
| active | a song is playing, or a key / knob / coin in the last 60 s |
| attract | attract mode is on (never sleeps by itself) |
| sleep | 10 min in idle, or Pause pressed twice: screens off, music stopped, queue cleared, attract off |
| shutdown | F20 Reboot, F21 Rebuild Playlist or F22 Shut Down pressed twice |

In sleep, any key or knob PRESS (or a coin) wakes it into active and does nothing
else; knob TURNS are ignored. It replaces the macro pad's `jukebox-keys` service
(same service keys) and the old nightly `screen-sleep.sh` / xbindkeys Pause key.

## Everything else only follows the state

Nothing else decides idle, active, attract or sleep on its own any more:

| Part | Reads | Shows |
| --- | --- | --- |
| Cabinet lights (`jukebox-bridge.py` 1.2+) | `/dev/shm/jukebox_mode` | idle look (starting, idle), active look, attract look, sleep look, off (shutdown). Key and coin events still flash the selecting / coin looks while awake. |
| Status page (`jukebox-status.py`) | `/dev/shm/jukebox_mode` | the Jukebox state row and Lights showing |
| Keypad Teensy | "S" / "A" sent by jukebox-state on sleep / wake | the waking press isn't used as a digit |

The old `/dev/shm/jukebox_sleep` flag is no longer made; jukebox-state removes
any left over. The installer also retires the older sleep pieces that kept
their own idle timer: the `screen-sleep.sh` cron job (mtmace and root
crontabs), the xbindkeys Pause binding, and the old scripts in `~/fruitbox`
(`screen-sleep.sh`, `install-screen-sleep.sh`, `install-sleep-key.sh`,
`jukebox-keys.py`, `jukebox-keys.service`, `install-keys.sh`). Copies go to
`~/fruitbox/backup-before-state-manager/retired`.

Service keys and Pause need two presses within 5 s.

## Playlist keys (pad keys 1, 2, 3)

**Parked since 1.5 (2026-11-17): keys 1-3 do nothing.** Fruitbox takes about 23
seconds for every playlist change (its own drawing, measured with any skin, not
the network), so stepping to a playlist isn't practical. `PLAYLIST_KEYS` is
empty; the note above it says how to switch them back on. What follows is how
they work when on.

The three pad keys that send Keypad 1 / 2 / 3 jump Fruitbox straight to a
playlist group (one press, no confirm):

| Key | Playlist (start of the group name) |
| --- | --- |
| Keypad 1 | All Songs |
| Keypad 2 | Oldies (Oldies - Rock & Roll) |
| Keypad 3 | Christmas |

Fruitbox can only step to the next group (Right Alt), so jukebox-state presses
Right Alt on its own virtual keyboard and reads the group Fruitbox shows
(`GROUP=` in `/dev/shm/jukebox_fruitbox.txt`, from the status page's hidden skin
box, updated once a second) until it is the right one. So it can take a few
seconds, and the groups in between flash by on screen. It stops, and logs why,
if that file is missing (status page not installed), if Fruitbox doesn't change
group, or if no group starts with that name (after one trip round, back where it
started). Pressing another playlist key meanwhile re-aims it. While asleep the
press only wakes the jukebox. Names are in `PLAYLIST_KEYS` at the top of
`jukebox-state.py`. Before 1.2 these keys picked favourite light themes in the
cabinet-light bridge.

Settings are at the top of `jukebox-state.py` (ACTIVE_SECONDS = 60, SLEEP_MINUTES = 10,
CONFIRM_SECONDS = 5).

## Screens stay off: Fruitbox is paused while asleep

On the Pi 5, Fruitbox drawing its screens switches the sleeping HDMI outputs
back on within 8-25 s, behind X's back (X still says "Monitor is Off"). Tested
2026-11-13: with Fruitbox paused the outputs stayed off for 60 s; resumed, they
were back on within 1 s. So sleep goes: keys to Fruitbox (stop music, clear
queue) -> 2 s -> pause Fruitbox (SIGSTOP) -> screens off. Wake: resume Fruitbox
-> screens on. Fruitbox is never left paused: it is resumed when the service
starts or stops, before F20/F21/F22, and if found paused while awake (logged
as WARNING). The log says "Fruitbox paused while asleep" / "Fruitbox resumed".

## Requests from the status page (1.4)

The status page's Control page (http://jukebox.local/control) can ask for Wake,
Sleep, Attract on / off, Reboot, Rebuild playlists and Shut down. It writes one
word to `/dev/shm/jukebox_request`; jukebox-state checks for it about once a
second, does exactly what the matching key would, deletes the file and logs
`status page asks: <word>`. Unknown words, requests older than 30 seconds, and
files not written by root or mtmace are ignored. The buttons come from
`WEB_REQUESTS` (and which ones ask "are you sure?" from `WEB_CONFIRM`) at the
top of `jukebox-state.py`, so the page only offers what the installed version can do.

## Volume after waking (1.3)

After a sleep the first song came out far too loud, although Fruitbox still
showed the set volume, until the knob was turned down and back up. Since 1.3
the state manager does that itself: one volume step up and back down (down and
back up at the maximum), so the volume ends where it was set, whatever that is.
It does this right at wake, before any song plays, and once more when the first
song after the wake starts. The log says `wake: volume re-applied` and
`first song after wake: volume re-applied`.

## Sound only to the DAC

On the Pi 5, turning the screens off and on (sleep) makes their HDMI sound
devices vanish and come back, and PipeWire moved the music onto them (no sound
from the jukebox). `51-jukebox-no-hdmi-audio.conf` is a WirePlumber 0.5 rule
that disables the HDMI sound devices, so the music can only go
Fruitbox -> Jukebox Bass -> DAC. The installer puts it in
`~/.config/wireplumber/wireplumber.conf.d/` for mtmace and restarts WirePlumber;
`off` removes it again. Screen video is not affected.

After every sleep and wake the log says `sound after sleep: ok ...` or
`WARNING sound after wake: ...` with what is wrong.

## Files

| File | What |
| --- | --- |
| jukebox-state.py | the state manager (installed to /usr/local/bin) |
| jukebox-state.service | its systemd service |
| 51-jukebox-no-hdmi-audio.conf | WirePlumber rule: no HDMI sound |
| install-state.sh | installs all of it (`off` undoes it) |

## Install

From PowerShell on the PC:

    scp -r C:\Users\MTmace\Documents\Jukebox\state-manager mtmace@Jukebox:/home/mtmace/fruitbox/

Then on the Pi (ssh mtmace@Jukebox):

    sudo bash /home/mtmace/fruitbox/state-manager/install-state.sh

Undo (puts the old jukebox-keys back):

    sudo bash /home/mtmace/fruitbox/state-manager/install-state.sh off

## Watch it

    cat /dev/shm/jukebox_mode
    tail -f /home/mtmace/fruitbox/jukebox-state.log

Self test without the Pi: `python3 jukebox-state.py --selftest`
