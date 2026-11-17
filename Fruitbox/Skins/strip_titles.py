#!/usr/bin/env python3
"""
Write Fruitbox's song list (fruitbox.db) for every folder under the genre
library, with a shortened title for the Firestar skin's title strips.

Fruitbox can't cut text at a character count, so the shortened title is
stored in the song's Custom field, which the skin shows on the strips
(SongDescription = ${CUSTOM_TAG}). The normal Title field keeps the full
title, so Now Playing, Coming Up and the second screen are unchanged.

The ISRC field holds "–  " plus the artist (the dash lives here so empty
rows of the second screen's list stay blank). Fruitbox's queue fields each keep
their own place in the queue, so the second screen's Coming Up list reads
${COMING_UP_CUSTOM_TAG} and ${COMING_UP_ISRC} while the main screen reads
${COMING_UP_TITLE} and ${COMING_UP_ARTIST}; that way both lists start at the
next song. Nothing else in the skin uses ISRC.

The Publisher field holds the file's format and bit rate, e.g.
"FLAC  ·  1,013 kbps", for the second screen's Now Playing. Fruitbox shows a
file's own PUBLISHER tag there instead if it has one (rare; LABEL is ignored).

Run it after genre_library.py, every time:

    python3 strip_titles.py /home/mtmace/JukeboxGenres

Fruitbox only rebuilds a fruitbox.db when the folder has changed since, so
these files stay put. If Fruitbox ever rebuilds one itself, that folder's
strips show no titles until this script runs again.

Needs: python3-mutagen   (sudo apt install python3-mutagen)
"""

import argparse
import os
import sys
import time

try:
    import mutagen
except ImportError:
    sys.exit("mutagen is missing: sudo apt install python3-mutagen")

MAX_CHARS = 25          # strip titles longer than this end in "..."
ELLIPSIS = "..."

MEDIA_EXT = {
    ".aac", ".aiff", ".alac", ".flac", ".m4a", ".m4b", ".mp3", ".mid", ".mpa",
    ".ogg", ".pcm", ".wav", ".wma",
    ".264", ".3gp", ".avi", ".divx", ".flv", ".m4v", ".mov", ".mp4", ".mkv",
    ".mpg", ".mpeg", ".ogv", ".wmv",
}

HEADER = (
    "# fruitbox version 3.02.02 database file\n"
    "# song entry format is Filename|SongTitle|Artist|AlbumTitle|AlbumArtist|"
    "Year|TrackNumber|LengthInSeconds|Publisher|ISRC|CustomTag[]|Genre\n"
)


def short(title, n=MAX_CHARS):
    if len(title) <= n:
        return title
    return title[:n].rstrip(" -,;:(") + ELLIPSIS


def clean(v):
    """One line, no field separators."""
    return " ".join(str(v).replace("|", "/").split())


def first(tags, *keys):
    for k in keys:
        try:
            v = tags.get(k)
        except Exception:
            v = None
        if v:
            return clean(v[0] if isinstance(v, list) else v)
    return ""


def number(s):
    """'1959-04-01' -> 1959, '3/12' -> 3, '' -> 0"""
    digits = ""
    for ch in s:
        if ch.isdigit():
            digits += ch
        elif digits:
            break
    return int(digits) if digits else 0


def audio_format(f, ext):
    """'FLAC  ·  1,013 kbps' from the file type and mutagen's stream info."""
    info = getattr(f, "info", None) if f is not None else None
    name = ext.lstrip(".").upper()
    codec = str(getattr(info, "codec", "") or "").lower()
    if name in ("M4A", "M4B", "MP4"):
        name = "ALAC" if "alac" in codec else "AAC"
    kbps = int(round((getattr(info, "bitrate", 0) or 0) / 1000)) if info is not None else 0
    return f"{name}  ·  {kbps:,} kbps" if kbps else name


def song_line(path):
    name = os.path.basename(path)
    stem = os.path.splitext(name)[0]
    try:
        f = mutagen.File(path, easy=True)
    except Exception:
        f = None
    tags = (f.tags if f is not None and f.tags is not None else {})
    length = int(round(f.info.length)) if f is not None and getattr(f, "info", None) else 0
    title = first(tags, "title") or clean(stem)
    fields = [
        name,
        title,
        first(tags, "artist") or "Unknown Artist",
        first(tags, "album") or "Unknown Album",
        first(tags, "albumartist") or "Unknown Album Artist",
        str(number(first(tags, "date", "year"))),
        str(number(first(tags, "tracknumber"))),
        str(length),
        audio_format(f, os.path.splitext(name)[1]),               # Publisher field = format, for the 2nd screen
        "–  " + (first(tags, "artist") or "Unknown Artist"),   # ISRC field = artist, for the 2nd screen's queue
        short(title),
        first(tags, "genre"),
    ]
    return "|".join(fields)


def write_folder(folder, names):
    lines = [song_line(os.path.join(folder, n)) for n in sorted(names)]
    db = os.path.join(folder, "fruitbox.db")
    tmp = db + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(HEADER + "".join(ln + "\n" for ln in lines))
    os.replace(tmp, db)
    # Fruitbox rebuilds a db that is older than its folder; keep ours newer.
    t = max(time.time(), os.stat(folder).st_mtime) + 2
    os.utime(db, (t, t))
    return len(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("genres", help="genre library folder made by genre_library.py")
    a = ap.parse_args()
    if not os.path.isdir(a.genres):
        sys.exit(f"not a folder: {a.genres}")
    folders = songs = 0
    for folder, _, files in os.walk(a.genres):
        media = [n for n in files if os.path.splitext(n)[1].lower() in MEDIA_EXT]
        if media:
            songs += write_folder(folder, media)
            folders += 1
    print(f"strip_titles: wrote fruitbox.db in {folders} folders ({songs} songs), "
          f"titles over {MAX_CHARS} characters shortened for the strips")


if __name__ == "__main__":
    main()
