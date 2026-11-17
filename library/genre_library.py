#!/usr/bin/env python3
"""
Build a genre-sorted view of a music library for Fruitbox v3's MusicGroup button.

Fruitbox can only filter by "music group", and a music group is a set of
MusicPath folders. It cannot group by the genre tag. This script reads the
genre tag of every song under SOURCE and creates DEST/<Genre>/... containing
hard links (no extra disk space) to the original files, plus each album's
cover art. It then rewrites the MusicPath lines in fruitbox.ini so each genre
folder is its own music group:

    MusicPath = /home/pi/JukeboxGenres/Rock = Rock
    MusicPath = /home/pi/JukeboxGenres/Soul = Soul
    ...

One press of the MusicGroup button then steps All Songs -> Rock -> Soul -> ...

A song with several genres goes in the group listed first in genre_map.txt.

Re-run it whenever you add music. It only touches DEST (and the ini, after
saving a .bak copy). Your original files are never moved or modified.

Needs: python3-mutagen   (sudo apt install python3-mutagen)
"""

import argparse
import os
import re
import shutil
import sys
from collections import Counter, defaultdict

try:
    import mutagen
except ImportError:
    sys.exit("mutagen is missing: sudo apt install python3-mutagen")

# Extensions Fruitbox v3 recognises (user guide, "Supported Media formats"),
# minus playlist/stream files (.m3u .pls) and .cda which carry no genre tag.
MEDIA_EXT = {
    ".aac", ".aiff", ".alac", ".flac", ".m4a", ".m4b", ".mp3", ".mid", ".mpa",
    ".ogg", ".pcm", ".wav", ".wma",
    ".264", ".3gp", ".avi", ".divx", ".flv", ".m4v", ".mov", ".mp4", ".mkv",
    ".mpg", ".mpeg", ".ogv", ".wmv",
}
ART_EXT = {".jpg", ".jpeg", ".png", ".bmp"}
MARKER = ".genre_library"          # marks DEST as ours, so we may clean it
KEEP = {MARKER, "fruitbox.db"}     # never delete these from DEST
MAX_GROUPS = 29                    # Fruitbox allows 30 incl. "All Songs"


def read_genres(path):
    """Every genre in the file's tag, in tag order (may be empty)."""
    try:
        f = mutagen.File(path, easy=True)
    except Exception:
        return []
    if not f or not f.tags:
        return []
    try:
        values = f.tags.get("genre") or []
    except Exception:
        return []
    out = []
    for v in values:
        # multi-genre tags: "Rock; Pop", "Rock/Pop", "Rock, Pop", "Rock\0Pop",
        # or several separate GENRE fields
        for g in re.split(r"[;/,|\x00]", str(v)):
            g = g.strip()
            if g and g not in out:
                out.append(g)
    return out


def pick_genre(genres, alias, order):
    """
    One group per song. Every genre on the song is mapped through genre_map.txt;
    the group listed FIRST in genre_map.txt wins, so "Pop; Country" -> Country
    when Country is above Pop. A genre that isn't listed but contains a listed
    group's name as a word also counts ("Country Pop", "Neo-Soul").
    Songs with no listed genre keep their first genre.
    """
    if not genres:
        return "Unknown"
    mapped = []
    for g in genres:
        t = alias.get(g.lower())
        if t is None:
            for target in order:
                if re.search(r"(?<![a-z])" + re.escape(target.lower()) + r"(?![a-z])", g.lower()):
                    t = target
                    break
        mapped.append(t or g)
    for target in order:
        if target in mapped:
            return target
    return mapped[0]


def load_map(path):
    """
    genre_map.txt lines:   Target Genre = alias, alias, alias
    plus an optional       Exclude = genre, genre   (those songs are left out)
    Returns (alias->target dict (lowercase keys), ordered list of targets,
    set of excluded genres (lowercase)).
    """
    alias, order, exclude = {}, [], set()
    if not path:
        return alias, order, exclude
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            target, _, rest = line.partition("=")
            target = target.strip()
            if not target:
                continue
            if target.lower() == "exclude":     # Exclude = Christmas, Holiday
                exclude.update(a.strip().lower() for a in rest.split(",") if a.strip())
                continue
            order.append(target)
            alias[target.lower()] = target
            for a in rest.split(","):
                a = a.strip()
                if a:
                    alias[a.lower()] = target
    return alias, order, exclude


def safe_name(genre):
    """Folder name: no spaces or punctuation, so the ini line parses cleanly."""
    s = re.sub(r"[^A-Za-z0-9]+", "_", genre.replace("&", "and")).strip("_")
    return s or "Unknown"


def group_label(genre):
    """Music group label: ',' and '=' are separators in a MusicPath line."""
    return re.sub(r"[,=]", " ", genre).strip() or "Unknown"


def link(src, dst, mode):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if mode == "hardlink":
        os.link(src, dst)
    elif mode == "symlink":
        os.symlink(os.path.realpath(src), dst)   # point at the real file, not a link to a link
    else:
        shutil.copy2(src, dst)


def same(src, dst, mode):
    try:
        if mode == "symlink":
            return os.path.islink(dst) and os.readlink(dst) == os.path.realpath(src)
        if mode == "hardlink":
            return os.path.samefile(src, dst)
        s, d = os.stat(src), os.stat(dst)
        return s.st_size == d.st_size and int(s.st_mtime) == int(d.st_mtime)
    except OSError:
        return False


def update_ini(ini, lines, all_label=None):
    with open(ini, encoding="utf-8") as fh:
        old = fh.read().splitlines()
    out, section, inserted = [], None, False
    for ln in old:
        m = re.match(r"\s*\[(.+?)\]", ln)
        if m:
            section = m.group(1).strip().lower()
        if section == "general" and all_label and \
                re.match(r"\s*MusicGroupAllSongsLabel\s*=", ln, re.I):
            out.append(f"  MusicGroupAllSongsLabel = {all_label}")
            continue
        if section == "general" and re.match(r"\s*MusicPath\s*=", ln, re.I):
            if not inserted:
                out.extend(lines)
                inserted = True
            continue
        out.append(ln)
        if m and section == "general" and not inserted:
            out.extend(lines)
            inserted = True
    if not inserted:
        out = ["[general]"] + lines + [""] + out
    shutil.copy2(ini, ini + ".bak")
    tmp = ini + ".tmp"                 # write then rename, so the ini is never half-written
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    os.replace(tmp, ini)


def main():
    home = os.path.expanduser("~")
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", default=os.path.join(home, "Music"),
                    help="your music library (default ~/Music)")
    ap.add_argument("--dest", default=os.path.join(home, "JukeboxGenres"),
                    help="genre view to build (default ~/JukeboxGenres)")
    ap.add_argument("--map", default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                  "genre_map.txt"),
                    help="genre merge/order file (default genre_map.txt next to this script)")
    ap.add_argument("--min-songs", type=int, default=10,
                    help="genres with fewer songs fold into 'Other' (default 10)")
    ap.add_argument("--mode", choices=["hardlink", "symlink", "copy"], default="hardlink",
                    help="hardlink needs SOURCE and DEST on the same drive (default)")
    ap.add_argument("--ini", help="fruitbox.ini to rewrite MusicPath lines in")
    ap.add_argument("--dry-run", action="store_true", help="report only, change nothing")
    a = ap.parse_args()

    src_root = os.path.realpath(a.source)
    dst_root = os.path.realpath(a.dest)
    if not os.path.isdir(src_root):
        sys.exit(f"source not found: {src_root}")
    if dst_root == src_root or dst_root.startswith(src_root + os.sep) \
            or src_root.startswith(dst_root + os.sep):
        sys.exit("DEST and SOURCE must not contain each other")
    if os.path.isdir(dst_root) and os.listdir(dst_root) \
            and not os.path.exists(os.path.join(dst_root, MARKER)):
        sys.exit(f"{dst_root} is not empty and was not made by this script; pick another --dest")

    alias, order, exclude = load_map(a.map if a.map and os.path.exists(a.map) else None)

    # 1. scan
    songs = []                       # (src_path, rel_dir, genre)
    excluded = 0
    for dirpath, dirnames, files in os.walk(src_root, followlinks=True):
        dirnames.sort()
        rel = os.path.relpath(dirpath, src_root)
        for fn in sorted(files):
            if os.path.splitext(fn)[1].lower() not in MEDIA_EXT:
                continue
            p = os.path.join(dirpath, fn)
            tags = read_genres(p)
            if exclude and any(t.lower() in exclude for t in tags):
                excluded += 1          # e.g. Christmas songs: not on the jukebox at all
                continue
            g = pick_genre(tags, alias, order)
            songs.append((p, rel, g))
    if not songs:
        sys.exit(f"no media files found under {src_root}")

    # 2. fold small genres into Other, cap the group count
    counts = Counter(g for _, _, g in songs)
    keep = {g for g, n in counts.items() if n >= a.min_songs and g not in ("Other", "Unknown")}
    ranked = sorted(keep, key=lambda g: -counts[g])
    keep = set(ranked[:MAX_GROUPS - 1])           # leave room for Other
    songs = [(p, r, g if g in keep else "Other") for p, r, g in songs]
    counts = Counter(g for _, _, g in songs)
    genres = [g for g in order if g in counts and g != "Other"] + \
             sorted(g for g in counts if g not in order and g != "Other")
    if "Other" in counts:
        genres.append("Other")

    # 3. desired DEST layout: DEST/<Genre>/<album dir>/<file> (+ album art)
    want = {}
    art_dirs = defaultdict(set)
    for p, rel, g in songs:
        d = os.path.normpath(os.path.join(dst_root, safe_name(g), rel))
        want[os.path.join(d, os.path.basename(p))] = p
        art_dirs[os.path.dirname(p)].add(d)
    for sdir, ddirs in art_dirs.items():
        for fn in os.listdir(sdir):
            if os.path.splitext(fn)[1].lower() in ART_EXT:
                for d in ddirs:
                    want[os.path.join(d, fn)] = os.path.join(sdir, fn)

    if exclude:
        print(f"left out {excluded} songs tagged {', '.join(sorted(exclude))}")
    print(f"{len(songs)} songs in {len(genres)} genres:")
    for g in genres:
        print(f"  {counts[g]:6d}  {g}")

    # The song count goes in the group label, so the skin's ${MUSIC_GROUP}
    # shows e.g. "Country (412)". Fruitbox has no count variable of its own.
    def ini_lines_for(gs):
        return [f"  MusicPath = {os.path.join(dst_root, safe_name(g))} = "
                f"{group_label(g)} ({counts[g]})" for g in gs]
    all_label = f"All Songs ({len(songs)})"
    ini_lines = ini_lines_for(genres)
    if a.dry_run:
        print("\nini lines that would be written:\n" + "\n".join(ini_lines))
        print(f"  MusicGroupAllSongsLabel = {all_label}")
        return

    # 4. sync DEST
    os.makedirs(dst_root, exist_ok=True)
    open(os.path.join(dst_root, MARKER), "a").close()
    removed = added = 0
    for dirpath, _, files in os.walk(dst_root, topdown=False):
        for fn in files:
            q = os.path.join(dirpath, fn)
            if fn in KEEP:
                continue
            if q not in want or not same(want[q], q, a.mode):
                os.remove(q)
                removed += 1
        if dirpath != dst_root:
            left = set(os.listdir(dirpath))
            if left <= {"fruitbox.db"}:
                for fn in left:
                    os.remove(os.path.join(dirpath, fn))
                os.rmdir(dirpath)
    for q, p in want.items():
        if not os.path.lexists(q):
            try:
                link(p, q, a.mode)
            except OSError as e:
                if a.mode == "hardlink" and e.errno in (18, 1, 95):   # EXDEV, EPERM, EOPNOTSUPP
                    sys.exit("hard links are not possible here (different drive or "
                             "FAT/exFAT). Re-run with --mode copy, or put --dest on the "
                             "same ext4 drive as your music.")
                raise
            added += 1
    print(f"\n{dst_root}: {added} added, {removed} removed")

    # Fruitbox refuses to start if any MusicPath folder is missing, so only
    # list genre folders that really exist now.
    missing = [g for g in genres if not os.path.isdir(os.path.join(dst_root, safe_name(g)))]
    if missing:
        print("skipping missing genre folders: " + ", ".join(missing))
        ini_lines = ini_lines_for([g for g in genres if g not in missing])
    if a.ini and ini_lines:
        update_ini(a.ini, ini_lines, all_label)
        print(f"updated MusicPath lines in {a.ini} (backup: {a.ini}.bak)")
    else:
        print("\nPaste these into [general] of fruitbox.ini, replacing the old MusicPath line(s):")
        print("\n".join(ini_lines))


if __name__ == "__main__":
    main()
