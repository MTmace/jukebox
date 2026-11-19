# Jukebox music library

The jukebox's songs and categories come from **playlists** made on Windows in
PlexMediaToolkit's **Jukebox** page. Your music stays on the Windows PC; the Pi never copies
it. It builds folders of **symlinks** (the Linux version of Windows shortcuts) that point at
the songs in each playlist, and Fruitbox plays from those folders. Each playlist becomes one
category on the genre button (Right Alt).

First-time setup: [SETUP-GUIDE.md](SETUP-GUIDE.md).

## How it works

```
Windows: PlexMediaToolkit, Jukebox page
        │  saves one file per category:
        ▼
\\YOUR-PC\...\MusicFiles\_Jukebox\01 Country.m3u8, 02 Saturday Night.m3u8, ...
        │  the same folder on the Pi: /mnt/music/_Jukebox (share mounted read-only)
        ▼
playlist_library.py   (nightly at 3:30 and 2 minutes after each boot, run by update-jukebox.sh)
        │  links each song once, writes the category list into fruitbox.ini
        ▼
/home/mtmace/JukeboxGroups/01, 01+02, 02, ...   ← Fruitbox plays from here
        │
strip_titles.py       writes the short titles for the skin's title strips
```

- **Order:** the number at the front of the file name is the order on the genre button.
  "All Songs" is kept and lists every song once.
- **A song in two playlists** is linked once into a folder that belongs to both categories
  (for example `01+02` = Country and Saturday Night). That's how All Songs avoids showing it twice.
- **Christmas and Holiday songs** (genre tag containing either word) stay in their own playlists
  but are left out of All Songs. The script makes All Songs itself (folders ending in `x`, e.g.
  `05x`, hold the songs left out), and Fruitbox's built-in one is off
  (`MusicGroupIncludeAllSongs = No`).
- **Duplicates:** the same song (same artist and title) from different albums is kept once:
  studio album, else single, else greatest hits, else live. Skipped ones are listed in
  `/home/mtmace/fruitbox/playlist-duplicates.txt`.
- **Work lists:** a playlist whose file name starts with `_` (like `_Ideas.m3u8`) is skipped.
- **Song order on screen:** artist, then album, then track number (skin setting `SortSongsBy`).
- Songs a playlist lists but the share doesn't have are written to
  `/home/mtmace/fruitbox/playlist-missing.txt`. Fix them with **Find match** on the Jukebox page.

## The files

All of these go in `/home/mtmace/fruitbox` on the Pi (like `C:\Users\mtmace\fruitbox`).

| File | What it does |
|---|---|
| `update-jukebox.sh` | The one you run by hand, and the one the nightly job runs. Runs `playlist_library.py`, then `strip_titles.py` if anything changed. Log: `library.log` |
| `playlist_library.py` | Reads the playlists and builds `~/JukeboxGroups` and the ini's MusicPath lines |
| `music_tags.py` | Tag reading and duplicate rules that `playlist_library.py` uses. Tags are cached in `/home/mtmace/.cache/playlist_tags.json`, so only new or changed files are read over the network |
| `strip_titles.py` | Writes Fruitbox's song list with shortened titles for the title strips |
| `setup-share.sh` | One-time setup: mounts the share, installs these files, adds the nightly job |

> **Start scripts with `bash` (or `python3` for .py files).** A file downloaded through
> Chromium loses its "can run" setting. To make them runnable on their own again (the nightly
> job needs this), type once: `chmod +x /home/mtmace/fruitbox/*.sh /home/mtmace/fruitbox/*.py`

## Quick commands

```
bash /home/mtmace/fruitbox/update-jukebox.sh            # update now (then reboot)
bash /home/mtmace/fruitbox/update-jukebox.sh --always   # same, and always rewrite the strip titles
bash /home/mtmace/fruitbox/update-jukebox.sh --force    # allow a run that removes over half the songs
python3 /home/mtmace/fruitbox/playlist_library.py --dry-run   # preview, changes nothing
tail -n 30 /home/mtmace/fruitbox/library.log            # what the last update did
ls /mnt/music                                           # is the Windows share connected?
crontab -l                                              # the automatic schedule
```

Fruitbox reads the folders when it starts, so changes show after the next reboot.

**Fruitbox's song database:** Fruitbox keeps a `fruitbox.db` in each folder and refreshes it
by itself when songs are added or removed. To force a full refresh (after fixing tags on
songs already on the jukebox):
```
find /home/mtmace/JukeboxGroups -name fruitbox.db -delete
sudo reboot
```

## Common tasks

| I want to... | Do this |
|---|---|
| Add or remove a song | Change the playlist in PlexMediaToolkit. Picked up at 3:30 am, or run `update-jukebox.sh`, then reboot |
| Add a category | Save a new numbered playlist (e.g. `06 Motown.m3u8`) in the `_Jukebox` folder, then update and reboot |
| Fix a slow third digit after the jukebox sits idle | Windows drops an idle share after 15 minutes. `setup-share.sh` adds a job that lists the share every 4 minutes to keep it awake. On the PC, set Power Options > "Turn off hard disk after" to Never |
| See what happened last night | `tail -n 30 /home/mtmace/fruitbox/library.log` |
| See the category folders | `ls /home/mtmace/JukeboxGroups` |

To edit a file on the Pi: `nano <path>`, then Ctrl+O and Enter to save, Ctrl+X to exit.

## Safety

- The share is mounted read-only. Nothing on the Windows PC is ever changed.
- If the share isn't mounted, there are no playlists, or more than half the songs would
  disappear since the last run, nothing changes and the log says why.
- `MODE=copy` in `update-jukebox.sh` still exists but isn't needed: Fruitbox plays through
  the symlinks (confirmed October 2026).
