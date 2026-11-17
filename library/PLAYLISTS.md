# Jukebox playlists: what the Pi does with them

Since November 2026 the jukebox's songs and categories come from **playlists**, not ratings or
genres. You make the playlists on Windows in PlexMediaToolkit's **Jukebox** page. The Pi turns
each playlist into one category on the genre button (Right Alt).

```
Windows: PlexMediaToolkit, Jukebox page
        │  saves one file per category:
        ▼
\\YOUR-PC\...\MusicFiles\_Jukebox\01 Country.m3u8, 02 Saturday Night.m3u8, ...
        │  the same folder on the Pi: /mnt/music/_Jukebox
        ▼
playlist_library.py   (nightly at 3:30 and after each boot, run by update-jukebox.sh)
        │  links each song once, writes the category list into fruitbox.ini
        ▼
/home/mtmace/JukeboxGroups/01, 01+02, 02, ...   ← Fruitbox plays from here
```

- **Order:** the number at the front of the file name is the order on the genre button.
  "All Songs" is kept and lists every song once.
- **A song in two playlists** is linked once into a folder that belongs to both categories
  (for example `01+02` = Country and Saturday Night). That's how All Songs avoids showing it twice.
- **Christmas and Holiday songs** (genre tag containing either word) stay in their own playlists
  but are left out of All Songs. All Songs is made by the script for this (its folders end in `x`,
  e.g. `05x`, for songs left out), and Fruitbox's built-in one is switched off
  (`MusicGroupIncludeAllSongs = No`).
- **Duplicates:** the same song (same artist and title) from different albums is kept once: studio
  album, else single, else greatest hits, else live. The kept version goes into every playlist any
  version was in. Skipped ones are listed in `/home/mtmace/fruitbox/playlist-duplicates.txt`.
  Tags are cached in `/home/mtmace/.cache/playlist_tags.json`; the script needs
  `jukebox_library.py` next to it in `/home/mtmace/fruitbox/`.
- **Work lists:** a playlist whose file name starts with `_` (like `_Ideas.m3u8`) is skipped.
- **Ratings and genre_map.txt are no longer used.** A song is on the jukebox only if it's in a playlist.
- **Song order on screen:** artist, then album, then track number (skin setting `SortSongsBy`).
- Songs a playlist lists but the share doesn't have are written to
  `/home/mtmace/fruitbox/playlist-missing.txt`. Fix them with **Find match** on the Jukebox page.
- **Safety:** if the share isn't mounted, there are no playlists, or more than half the songs
  would disappear since the last run, nothing changes and the log says why. To allow a big
  clean-out on purpose: `bash /home/mtmace/fruitbox/update-jukebox.sh --force`

## One-time setup on the Pi

Do these on the Pi, one command at a time. `/home/mtmace/fruitbox` is like `C:\Users\mtmace\fruitbox`.

1. **Keep a copy of today's nightly script and settings**, so you can go back:
   ```
   cp /home/mtmace/fruitbox/update-jukebox.sh /home/mtmace/fruitbox/update-jukebox.sh.old
   cp /home/mtmace/fruitbox/fruitbox.ini /home/mtmace/fruitbox/fruitbox.ini.before-playlists
   ```
2. **Download the two new files** from GitHub in Chromium (branch `claude/project-thread-d1wxff`,
   folder `library`), and save both into `/home/mtmace/fruitbox/`, replacing the old
   `update-jukebox.sh`:
   - `playlist_library.py`
   - `update-jukebox.sh`
3. **Make them runnable again** (Chromium downloads lose that setting):
   ```
   chmod +x /home/mtmace/fruitbox/*.sh /home/mtmace/fruitbox/*.py
   ```
4. **Preview without changing anything.** This lists your playlists and song counts, and the
   lines it would write to fruitbox.ini:
   ```
   python3 /home/mtmace/fruitbox/playlist_library.py --dry-run
   ```
   If it says no `_Jukebox` folder was found, save at least one playlist in PlexMediaToolkit first.
5. **Build it for real:**
   ```
   bash /home/mtmace/fruitbox/update-jukebox.sh --always
   tail -n 30 /home/mtmace/fruitbox/library.log
   ```
6. **Song order in the skin.** Open the skin settings:
   ```
   sudo nano "/opt/fruitbox/skins/Firestar Ultrawide/fruitbox.cfg"
   ```
   Find these two lines:
   ```
   SortSongsBy = Title
   SortSongsBy = Artist
   ```
   and replace them with these three (nothing else in the file changes):
   ```
   SortSongsBy = TrackNumber
   SortSongsBy = Album
   SortSongsBy = Artist
   ```
   Save with Ctrl+O, Enter, then Ctrl+X. If the songs come out ordered by track number instead of
   artist, reverse the three lines (Fruitbox may treat the first line as the main one).
7. **Restart Fruitbox** (or reboot) and check: the genre button steps through your playlists in
   order, each shows only its songs, and All Songs shows each song once.

## Going back to the old way

```
cp /home/mtmace/fruitbox/update-jukebox.sh.old /home/mtmace/fruitbox/update-jukebox.sh
cp /home/mtmace/fruitbox/fruitbox.ini.before-playlists /home/mtmace/fruitbox/fruitbox.ini
```
Then put the two old `SortSongsBy` lines back and reboot. The old genre folders in
`/home/mtmace/JukeboxGenres` are left untouched by the new script.
