# Jukebox music library: how it works

> **Since November 2026 the jukebox uses playlists made in PlexMediaToolkit instead of ratings and genres.** See [PLAYLISTS.md](PLAYLISTS.md). The rating and genre steps below describe the old way (kept for reference).

Your music stays on the Windows media server. The Pi never copies it. Instead the Pi
builds folders of **symlinks** (the Linux version of Windows shortcuts) that point at
just the songs you picked, sorted into genres. Fruitbox plays from those folders.

Everything here runs on the **Pi**, except the one PowerShell script, which runs on Windows.

## Where things live

| On the Pi | Windows equivalent | What it is |
|---|---|---|
| `/mnt/music` | a mapped drive, like `M:` | Your Windows share `\\192.168.1.20\MusicFiles`, read-only |
| `/home/mtmace/fruitbox` | `C:\Users\mtmace\fruitbox` | All the jukebox scripts and settings |
| `/home/mtmace/JukeboxLibrary` | a folder of shortcuts | Shortcuts to the songs you picked, same folders as on the share |
| `/home/mtmace/JukeboxGenres` | a folder of shortcuts | Same songs, one folder per genre. **Fruitbox plays from here** |
| `/opt/fruitbox` | `C:\Program Files\fruitbox` | The Fruitbox program and skins. Left as installed |

`~` in Linux means your home folder, so `~/fruitbox` is the same as `/home/mtmace/fruitbox`.

## The process, step by step

```
Windows: \\192.168.1.20\MusicFiles   (you rate and tag songs here)
        │
        │  mounted read-only on the Pi at /mnt/music
        ▼
1. jukebox_library.py   picks songs rated 4+ stars OR with Grouping = Jukebox,
        │               skips duplicate copies (live / greatest hits)
        ▼
   /home/mtmace/JukeboxLibrary
        │
2. genre_library.py     sorts each song into one genre using genre_map.txt,
        │               and writes the genre list into fruitbox.ini
        ▼
   /home/mtmace/JukeboxGenres/Country, /Rock, /Soul, ...
        │
3. Fruitbox             reads fruitbox.ini; the genre button (Right Alt) steps through the folders
```

**When it runs:** steps 1 and 2 run automatically every night at 3:30 am and 2 minutes after
every boot (a cron job, the Linux version of Task Scheduler). Fruitbox reads the folders when
it starts, so changes show after the next reboot.

## The files

### On the Pi, in /home/mtmace/fruitbox

> **Always start scripts with `bash` (or `python3` for .py files).** A file downloaded through Chromium loses its "can run" setting, so typing just its path gives "Permission denied". `bash /path/to/script.sh` runs it anyway. To make the scripts runnable on their own again (the nightly job needs this), type once: `chmod +x /home/mtmace/fruitbox/*.sh`

**update-jukebox.sh** is the one you run by hand, and the one the nightly job runs. It runs
step 1, then step 2 only if songs were added or removed.
- Your selection rule is the `SELECT=` line at the top. Examples are in the file.
- Run it: `bash /home/mtmace/fruitbox/update-jukebox.sh`
- Force the genre rebuild even when no songs changed (needed after editing genre_map.txt):
  `bash /home/mtmace/fruitbox/update-jukebox.sh --always`
- Its log is `/home/mtmace/fruitbox/library.log`

**jukebox_library.py** does step 1. You normally don't run it directly. It reads the rating
inside each file (`FMPS_RATING`, which your library manager writes; 0.8 = 4 stars), not
Plex's database. It remembers tags in `/home/mtmace/.cache/jukebox_library.json`, so only
new or changed files are read over the network. The first run on ~11,000 songs takes 20+ minutes.
To preview what it would pick without changing anything:
`python3 /home/mtmace/fruitbox/jukebox_library.py --dry-run --list --min-stars 4 --tag grouping=Jukebox`

**duplicates.txt** is written by step 1. When the same song (same artist and title) is on
several albums, only one copy goes on the jukebox: studio album first, then single, then
greatest hits or compilation, then live. Each line shows what was skipped and what was kept.
To turn this off, add `--keep-duplicates` to the `SELECT=` line.

**genre_library.py** does step 2. A song can carry several genres; it goes in the group
listed first in genre_map.txt. Where a song goes:

1. Its genre is on a line in genre_map.txt: that line's group.
2. Its genre contains a group name as a word ("Country Pop" goes to Country, "Neo Soul"
   to R&B because Soul is on the R&B line): that group.
3. Its genre matches nothing: it keeps its own name. With 10 or more such songs it gets
   its own group on the genre button; with fewer, those songs go to "Other".
4. No genre tag at all: "Other".
5. Tagged with a genre on the `Exclude =` line (Christmas, Holiday): left off the
   jukebox completely.

Every song except excluded ones is also in "All Songs".

**genre_map.txt** is the file you edit to control genres. Each line is
`Group Name = genre, genre, ...`. The order of lines is both the priority (Country first,
so "Pop; Country" goes to Country) and the order the genre button cycles through. To merge
small genres, add them to an existing line. Your music files are never changed.

**fruitbox.ini** holds Fruitbox's settings for this jukebox (buttons, credits, attract mode).
Step 2 rewrites its `MusicPath` lines, one per genre folder, so don't edit those lines by hand.

**launch-fruitbox.sh** starts Fruitbox with this fruitbox.ini and restarts it if it crashes.
It runs automatically at login. Typing `fruitbox` in a terminal runs it too, because of the
alias line added to `/home/mtmace/.bashrc`.

**setup-share.sh** is one-time setup, already done: mounts the share, stores the Windows
password in `/etc/jukebox-share.cred`, copies the scripts here, and adds the nightly job.
Run it again only if the server's address, share name or password changes, from the
`library` folder of the unzipped jukebox-setup:
`bash setup-share.sh //192.168.1.20/MusicFiles mtmace`

### On Windows

**Check-FlacRatings.ps1** reads the ratings inside your FLAC files and shows how many songs
the Pi would pick, so you can check the Pi's numbers. It changes nothing.
```
powershell -ExecutionPolicy Bypass -File .\Check-FlacRatings.ps1 -Path "G:\PlexServerData\Music\MusicFiles"
```
Add `-Csv "$HOME\Desktop\ratings.csv"` to also save a per-song list.

### Guides

**SETUP-GUIDE.md** is the first-time setup walkthrough. This README is for day-to-day use.

## Quick commands

Type these in a terminal on the Pi (the black-box icon on the desktop, like Command Prompt).

**Fruitbox**
```
fruitbox                     # start Fruitbox (from a terminal on the jukebox screen)
```
- Quit: press **Esc** on the keyboard. Fruitbox closes to the desktop and stays closed.
- Fruitbox starts by itself after every reboot, so normally you don't need to start it.
- Its log: `tail -n 30 /home/mtmace/fruitbox/fruitbox.log`

**Fruitbox's song database**

Fruitbox keeps a small `fruitbox.db` file in each genre folder and refreshes it on its own at
start-up when songs are added or removed. To force a full refresh (for example after fixing
tags on songs that are already on the jukebox), delete those files and restart:
```
find /home/mtmace/JukeboxGenres -name fruitbox.db -delete
sudo reboot
```
The first start after this takes longer while Fruitbox reads every song again.

**Music library**
```
bash /home/mtmace/fruitbox/update-jukebox.sh            # update the song picks now (then reboot)
bash /home/mtmace/fruitbox/update-jukebox.sh --always   # same, and always rebuild the genres
tail -n 30 /home/mtmace/fruitbox/library.log       # what the last update did
ls /mnt/music                                      # is the Windows share connected?
crontab -l                                         # show the automatic schedule
```

**The Pi**
```
sudo reboot                  # restart (like Windows Restart)
sudo shutdown now            # turn off safely before cutting power
```

## Common tasks

| I want to... | Do this |
|---|---|
| Add or remove a song | Change its rating or Grouping tag on Windows. Picked up at 3:30 am, or run `bash /home/mtmace/fruitbox/update-jukebox.sh`, then reboot |
| Change which songs qualify | Edit `SELECT=` in `/home/mtmace/fruitbox/update-jukebox.sh` |
| Fix a slow third digit after the jukebox sits idle | Windows drops an idle share after 15 minutes, so the first song picked waits while the Pi reconnects. Keep it awake: `(crontab -l; echo "*/4 * * * * ls /mnt/music >/dev/null 2>&1") \| crontab -` (new installs of `setup-share.sh` already do this). On the PC, set Power Options > "Turn off hard disk after" to Never |
| Change or merge genres | Edit `/home/mtmace/fruitbox/genre_map.txt`, run `bash /home/mtmace/fruitbox/update-jukebox.sh --always`, reboot |
| Leave a genre off the jukebox | Add it to the `Exclude =` line at the bottom of `/home/mtmace/fruitbox/genre_map.txt` (Christmas and Holiday are there now), run `bash /home/mtmace/fruitbox/update-jukebox.sh --always`, reboot |
| See what happened last night | `tail -n 30 /home/mtmace/fruitbox/library.log` |
| See which duplicates were skipped | `less /home/mtmace/fruitbox/duplicates.txt` (q to quit) |
| See the genre folders | `ls /home/mtmace/JukeboxGenres` |
| Count the picked songs | `find /home/mtmace/JukeboxLibrary -type l -name '*.flac' \| wc -l` |

To edit a file on the Pi: `nano <path>`, then Ctrl+O and Enter to save, Ctrl+X to exit.
Type commands by hand; pasting into the Pi terminal sometimes adds stray characters like `^[[200~`.

## Safety

- The share is mounted read-only. Nothing on the Windows PC is ever changed.
- If the server is off or the share isn't mounted, the run stops and the jukebox keeps the
  songs it had.
- A run that would remove more than half the songs stops too, in case the share came up
  half-empty. Override once with `--force` if the drop is real.

## Symlinks

Confirmed on the Pi (October 2026): Fruitbox loads and plays songs through the symlinks, so
nothing is copied to the Pi's 64 GB drive. `MODE=copy` in `update-jukebox.sh` still exists
but isn't needed.
