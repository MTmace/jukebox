#!/usr/bin/env python3
"""
Build the jukebox's categories from playlist files, without copying music.

The playlists are made on Windows with the Jukebox page of PlexMediaToolkit
and saved in the share's _Jukebox folder, one .m3u8 file per category:

    \\\\YOUR-PC\\...\\MusicFiles\\_Jukebox\\01 Country.m3u8
    \\\\YOUR-PC\\...\\MusicFiles\\_Jukebox\\02 Saturday Night.m3u8

On the Pi the share is /mnt/music, so that is /mnt/music/_Jukebox. The number
at the front is the order on the genre button, the rest is the name shown.
A file whose name starts with _ is a work list and is skipped. Each song line
is a path relative to the share, with forward slashes:

    Johnny Cash/The Essential Johnny Cash/05 Ring of Fire.flac

Only songs in a playlist are on the jukebox; ratings are not used.

A song may be in several playlists. Fruitbox lets one folder belong to
several music groups, so each song is linked ONCE, into a folder for its exact
set of playlists, and that folder's MusicPath line names all of them:

    MusicPath = /home/mtmace/JukeboxGroups/01+02 = Country (412), Saturday Night (88)

That way "All Songs" lists every song once and NoDuplicates still works.
Album cover art is linked next to the songs.

All Songs is our own group (Fruitbox's built-in one is switched off with
MusicGroupIncludeAllSongs = No), so that songs whose genre tag contains
Christmas or Holiday can stay in their own playlists but are left out of All
Songs. Their folders end in "x" (e.g. 05x) and their MusicPath lines don't
name All Songs. Change the words with --exclude-from-all.

Duplicates: the same song (same artist and title, ignoring "(Remastered)"
and the like) from different albums is kept only once. The best version
wins (studio album > single > greatest hits > live) and it goes into every
playlist any of the versions was in. The skipped versions are listed in
--dup-report. Turn this off with --keep-duplicates. Tags are read with
music_tags.py and cached in --tag-cache, so re-runs are quick.

It then rewrites the MusicPath lines (in playlist order) and the All Songs
label in fruitbox.ini. Run strip_titles.py on DEST afterwards.

Safety: it changes nothing when the share isn't mounted, when there are no
playlists, or when more than --max-remove percent of the songs would vanish
since the last run (use --force after a big clean-out). Songs listed in a
playlist but not found on the share are written to --missing-log.

Exit codes: 0 = nothing changed, 3 = songs or groups changed, other = error.
"""

import argparse
import json
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from music_tags import read_tags, song_key, version_kind, KIND_NAMES  # noqa: E402

MEDIA_EXT = {".mp3", ".flac", ".ogg", ".oga", ".wav", ".m4a", ".mp4", ".aac", ".opus",
             ".wma", ".aif", ".aiff", ".ape", ".wv", ".mpc", ".mpg", ".mpeg", ".avi",
             ".mkv", ".mov", ".m4v", ".webm"}
ART_EXT = {".jpg", ".jpeg", ".png", ".bmp"}
MARKER = ".playlist_library"        # marks DEST as ours (holds last run's counts)
KEEP = {MARKER, "fruitbox.db"}      # never delete these from DEST
MAX_GROUPS = 29                     # Fruitbox allows 30 incl. "All Songs"
PLAYLIST_EXT = ".m3u8"
TAG_FIELDS = ["artist", "albumartist", "title", "album", "compilation",
              "releasetype", "musicbrainz_albumtype", "genre"]
TAG_CACHE_VERSION = 1


# ---------- playlists ----------

def parse_name(filename):
    """'01 Country.m3u8' -> (1, 'Country'); '_Ideas.m3u8' -> None (work list)."""
    name = os.path.splitext(filename)[0].strip()
    if name.startswith("_"):
        return None
    m = re.match(r"^(\d{1,3})\s+(.+)$", name)
    return (int(m.group(1)), m.group(2).strip()) if m else (10**6, name)


def read_playlist(path):
    """Song lines in file order, '\\' turned into '/', duplicates dropped."""
    out, seen = [], set()
    with open(path, encoding="utf-8-sig", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            rel = line.replace("\\", "/").lstrip("/")
            key = rel.lower()
            if key not in seen:
                seen.add(key)
                out.append(rel)
    return out


def load_playlists(folder):
    lists = []
    for fn in os.listdir(folder):
        if not fn.lower().endswith(PLAYLIST_EXT):
            continue
        parsed = parse_name(fn)
        if parsed is None:
            continue
        order, label = parsed
        lists.append((order, label.lower(), label, read_playlist(os.path.join(folder, fn))))
    lists.sort()
    return [(label, songs) for _, _, label, songs in lists]


def find_playlist_folder(share):
    """The share's _Jukebox folder: at the top, or up to 3 folders down."""
    for depth_root, dirs, _ in os.walk(share):
        depth = depth_root[len(share):].count(os.sep)
        if "_Jukebox" in dirs:
            return os.path.join(depth_root, "_Jukebox")
        if depth >= 2:
            dirs[:] = []
        else:
            dirs[:] = sorted(d for d in dirs if not d.startswith("."))
    return None


class CaseInsensitiveResolver:
    """Windows ignores case in paths, Linux doesn't. If a playlist path doesn't
    match exactly (e.g. a folder was renamed 'The beatles' -> 'The Beatles'),
    look each part up ignoring case. Folder listings are cached."""

    def __init__(self, root):
        self.root = root
        self.cache = {}

    def _names(self, folder):
        if folder not in self.cache:
            try:
                self.cache[folder] = {n.lower(): n for n in os.listdir(folder)}
            except OSError:
                self.cache[folder] = {}
        return self.cache[folder]

    def resolve(self, rel):
        exact = os.path.join(self.root, rel)
        if os.path.isfile(exact):
            return exact
        cur = self.root
        for part in rel.split("/"):
            real = self._names(cur).get(part.lower())
            if real is None:
                return None
            cur = os.path.join(cur, real)
        return cur if os.path.isfile(cur) else None


# ---------- folders and ini ----------

def group_label(label):
    """Music group label: ',' and '=' are separators in a MusicPath line."""
    return re.sub(r"\s+", " ", re.sub(r"[,=]", " ", label)).strip() or "Unknown"


def link(src, dst, mode):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if mode == "symlink":
        os.symlink(src, dst)
    else:
        shutil.copy2(src, dst)


def same(src, dst, mode):
    try:
        if mode == "symlink":
            return os.path.islink(dst) and os.readlink(dst) == src
        s, d = os.stat(src), os.stat(dst)
        return s.st_size == d.st_size and int(s.st_mtime) == int(d.st_mtime)
    except OSError:
        return False


def update_ini(ini, lines, all_label, include_all=True):
    with open(ini, encoding="utf-8") as fh:
        old = fh.read().splitlines()
    out, section, inserted = [], None, False
    seen_include = False
    for ln in old:
        m = re.match(r"\s*\[(.+?)\]", ln)
        if m:
            section = m.group(1).strip().lower()
        if section == "general" and re.match(r"\s*MusicGroupAllSongsLabel\s*=", ln, re.I):
            out.append(f"  MusicGroupAllSongsLabel = {all_label}")
            continue
        if section == "general" and re.match(r"\s*MusicGroupIncludeAllSongs\s*=", ln, re.I):
            if not include_all:
                out.append("  MusicGroupIncludeAllSongs = No")
            else:
                out.append("  MusicGroupIncludeAllSongs = Yes")
            seen_include = True
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
    if not seen_include:               # add it right after the MusicPath lines
        val = "Yes" if include_all else "No"
        at = out.index(lines[-1]) + 1 if lines and lines[-1] in out else len(out)
        out.insert(at, f"  MusicGroupIncludeAllSongs = {val}")
    new = "\n".join(out) + "\n"
    if new == "\n".join(old) + "\n":
        return False
    shutil.copy2(ini, ini + ".bak")
    tmp = ini + ".tmp"                 # write then rename, so the ini is never half-written
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(new)
    os.replace(tmp, ini)
    return True


def load_tags(paths, cache_file):
    """{path: fields} for the songs, reading only new or changed files."""
    try:
        with open(cache_file, encoding="utf-8") as fh:
            c = json.load(fh)
        cache = c["files"] if c.get("version") == TAG_CACHE_VERSION \
            and c.get("fields") == TAG_FIELDS else {}
    except (OSError, ValueError, KeyError):
        cache = {}
    out, new_cache, read = {}, {}, 0
    for p in paths:
        try:
            st = os.stat(p)
        except OSError:
            out[p] = {}
            continue
        sig = [st.st_size, int(st.st_mtime)]
        hit = cache.get(p)
        if hit and hit[0] == sig:
            fields = hit[1]
        else:
            _, fields = read_tags(p)
            fields = {k: fields[k] for k in TAG_FIELDS if k in fields}
            read += 1
        new_cache[p] = [sig, fields]
        out[p] = fields
    return out, new_cache, read


def save_tags(cache_file, files):
    os.makedirs(os.path.dirname(os.path.abspath(cache_file)), exist_ok=True)
    tmp = cache_file + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump({"version": TAG_CACHE_VERSION, "fields": TAG_FIELDS, "files": files}, fh)
    os.replace(tmp, cache_file)


def is_excluded(fields, words):
    genres = " ".join(str(g) for g in fields.get("genre", [])).lower()
    return any(w in genres for w in words)


def main():
    home = os.path.expanduser("~")
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--share", default="/mnt/music",
                    help="the mounted music share; playlist paths are relative to it (default /mnt/music)")
    ap.add_argument("--playlists",
                    help="playlist folder (default: the share's _Jukebox folder, found automatically)")
    ap.add_argument("--dest", default=os.path.join(home, "JukeboxGroups"),
                    help="folders Fruitbox plays from (default ~/JukeboxGroups)")
    ap.add_argument("--mode", choices=["symlink", "copy"], default="symlink")
    ap.add_argument("--ini", help="fruitbox.ini to rewrite MusicPath lines in")
    ap.add_argument("--missing-log", default=os.path.join(here, "playlist-missing.txt"),
                    help="where to list songs not found on the share")
    ap.add_argument("--exclude-from-all", default="christmas,holiday",
                    help="genre words (comma separated) that keep a song out of All Songs "
                         "(default christmas,holiday; empty = use Fruitbox's own All Songs)")
    ap.add_argument("--keep-duplicates", action="store_true",
                    help="keep every version of a song instead of only the best one")
    ap.add_argument("--dup-report", default=os.path.join(here, "playlist-duplicates.txt"),
                    help="where to list the duplicate versions that were skipped")
    ap.add_argument("--tag-cache", default=os.path.join(home, ".cache", "playlist_tags.json"),
                    help="tag cache file")
    ap.add_argument("--max-remove", type=int, default=50,
                    help="refuse when more than this percent of songs would vanish (default 50)")
    ap.add_argument("--force", action="store_true", help="skip the --max-remove check")
    ap.add_argument("--no-mount-check", action="store_true",
                    help="allow a --share that is not a mount point (testing)")
    ap.add_argument("--dry-run", action="store_true", help="report only, change nothing")
    a = ap.parse_args()

    share = os.path.realpath(a.share)
    dst_root = os.path.realpath(a.dest)
    if not os.path.isdir(share):
        sys.exit(f"share not found: {share} (is it mounted?); jukebox left as it is")
    if not a.no_mount_check and not os.path.ismount(share):
        sys.exit(f"{share} is not mounted; jukebox left as it is")
    if dst_root == share or dst_root.startswith(share + os.sep):
        sys.exit("--dest must not be inside the share")
    if os.path.isdir(dst_root) and os.listdir(dst_root) \
            and not os.path.exists(os.path.join(dst_root, MARKER)):
        sys.exit(f"{dst_root} is not empty and was not made by this script; pick another --dest")

    pl_dir = a.playlists or find_playlist_folder(share)
    if not pl_dir or not os.path.isdir(pl_dir):
        sys.exit(f"no _Jukebox playlist folder found under {share}; jukebox left as it is")
    # Playlist paths are relative to the folder that holds _Jukebox (MusicFiles).
    lib_root = os.path.dirname(os.path.realpath(pl_dir))
    playlists = load_playlists(pl_dir)
    if not playlists:
        sys.exit(f"no playlists in {pl_dir}; jukebox left as it is")
    if len(playlists) > MAX_GROUPS:
        print(f"WARNING: {len(playlists)} playlists, Fruitbox shows {MAX_GROUPS} plus All Songs; "
              f"skipping: {', '.join(l for l, _ in playlists[MAX_GROUPS:])}")
        playlists = playlists[:MAX_GROUPS]

    # 1. resolve every song; remember which playlists (by position) hold it
    resolver = CaseInsensitiveResolver(lib_root)
    member = {}                        # real path -> sorted playlist indexes
    rel_of = {}                        # real path -> relative path (for the folder layout)
    counts = [0] * len(playlists)
    missing = []
    for i, (label, songs) in enumerate(playlists):
        for rel in songs:
            if os.path.splitext(rel)[1].lower() not in MEDIA_EXT:
                continue
            path = resolver.resolve(rel)
            if path is None:
                missing.append(f"{label}\t{rel}")
                continue
            idx = member.setdefault(path, [])
            if i not in idx:
                idx.append(i)
                counts[i] += 1
            rel_of[path] = os.path.relpath(path, lib_root)
    if not member:
        sys.exit("none of the playlist songs were found on the share; jukebox left as it is")

    # 1b. tags: genre for the All Songs exclusion, artist/title for duplicates
    words = [w.strip().lower() for w in a.exclude_from_all.split(",") if w.strip()]
    tags, tag_cache, tags_read = load_tags(sorted(member), a.tag_cache)
    dup_lines = []
    if not a.keep_duplicates:
        by_key = {}
        for path in member:
            k = song_key(tags.get(path, {}))
            if k:
                by_key.setdefault(k, []).append(path)
        for k, paths in by_key.items():
            if len(paths) < 2:
                continue
            best = min(paths, key=lambda p: (version_kind(rel_of[p], tags[p]), rel_of[p]))
            bkind = KIND_NAMES[version_kind(rel_of[best], tags[best])]
            for p in paths:
                if p == best:
                    continue
                for i in member.pop(p):
                    if i not in member[best]:
                        member[best].append(i)
                dup_lines.append(f"SKIP [{KIND_NAMES[version_kind(rel_of[p], tags[p])]}] "
                                 f"{rel_of[p]}\n  KEEP [{bkind}] {rel_of[best]}")
    counts = [0] * len(playlists)
    for idx in member.values():
        for i in idx:
            counts[i] += 1
    excluded = {p for p in member if words and is_excluded(tags.get(p, {}), words)}

    # 2. one folder per exact set of playlists: DEST/01+03/<artist>/<album>/<file>
    #    songs left out of All Songs go in a folder ending in x: DEST/05x/...
    def folder_of(idx, excl):
        return "+".join(f"{i + 1:02d}" for i in sorted(idx)) + ("x" if excl else "")

    want = {}
    art_dirs = {}
    combos = {}                        # folder -> (playlist indexes, left out of All Songs)
    for path, idx in member.items():
        excl = path in excluded
        key = folder_of(idx, excl)
        combos[key] = (sorted(idx), excl)
        d = os.path.join(dst_root, key, os.path.dirname(rel_of[path]))
        want[os.path.join(d, os.path.basename(path))] = path
        art_dirs.setdefault(os.path.dirname(path), set()).add(d)
    for sdir, ddirs in art_dirs.items():
        try:
            names = os.listdir(sdir)
        except OSError:
            continue
        for fn in names:
            if os.path.splitext(fn)[1].lower() in ART_EXT:
                for d in ddirs:
                    want[os.path.join(d, fn)] = os.path.join(sdir, fn)

    total = len(member)
    in_all = total - len(excluded)
    own_all = bool(words) and in_all > 0
    labels = [f"{group_label(l)} ({counts[i]})" for i, (l, _) in enumerate(playlists)]
    all_label = f"All Songs ({in_all if own_all else total})"
    # Folders in playlist order: by their first playlist, then the rest. Groups
    # appear on the genre button in the order the lines first name them, so a
    # line that includes All Songs goes first to keep All Songs at the front.
    ordered = sorted(combos, key=lambda k: combos[k])
    if own_all:
        first = next(k for k in ordered if not combos[k][1])
        ordered.remove(first)
        ordered.insert(0, first)

    def line(k):
        idx, excl = combos[k]
        names = ([all_label] if own_all and not excl else []) + [labels[i] for i in idx]
        return f"  MusicPath = {os.path.join(dst_root, k)} = " + ", ".join(names)
    ini_lines = [line(k) for k in ordered]

    print(f"{total} songs in {len(playlists)} playlists ({pl_dir}):")
    for i, (label, _) in enumerate(playlists):
        print(f"  {counts[i]:6d}  {label}")
    if missing:
        print(f"{len(missing)} playlist songs not found on the share, see {a.missing_log}")
    print(f"tags read for {tags_read} new or changed songs")
    if dup_lines:
        print(f"{len(dup_lines)} duplicate versions skipped, see {a.dup_report}")
    if own_all:
        print(f"All Songs: {in_all} songs ({len(excluded)} left out for genre "
              f"{' / '.join(words)})")

    # Group order on the genre button follows the order groups first appear in
    # the MusicPath lines. Warn if a playlist only shares songs with an earlier one
    # in a way that pulls a later playlist ahead of it.
    seen, first_order = set(), []
    for k in ordered:
        for i in combos[k][0]:
            if i not in seen:
                seen.add(i)
                first_order.append(i)
    if first_order != sorted(first_order):
        print("note: the genre button may list "
              + ", ".join(playlists[i][0] for i in first_order)
              + " in that order (a playlist's songs are all also in another one)")

    # 3. the --max-remove guard, against last run's song count
    marker = os.path.join(dst_root, MARKER)
    old_total = 0
    try:
        with open(marker, encoding="utf-8") as fh:
            old_total = json.load(fh).get("songs", 0)
    except (OSError, ValueError):
        pass
    if old_total and not a.force and total < old_total * (100 - a.max_remove) / 100:
        sys.exit(f"would drop from {old_total} to {total} songs, over the {a.max_remove}% limit; "
                 "jukebox left as it is. If that's intended, run again with --force.")

    if a.dry_run:
        save_tags(a.tag_cache, tag_cache)  # only a cache: makes the real run quick
        print("\nini lines that would be written:\n" + "\n".join(ini_lines))
        print(f"  MusicGroupIncludeAllSongs = {'No' if own_all else 'Yes'}")
        print(f"  MusicGroupAllSongsLabel = {all_label}")
        if dup_lines:
            print("\nfirst duplicates:\n" + "\n".join(sorted(dup_lines)[:10]))
        return 0

    if a.missing_log:
        with open(a.missing_log, "w", encoding="utf-8") as fh:
            fh.write("# playlist\tsong path (not found on the share)\n")
            fh.write("\n".join(missing) + ("\n" if missing else ""))
    if a.dup_report:
        with open(a.dup_report, "w", encoding="utf-8") as fh:
            fh.write(f"{len(dup_lines)} duplicate versions skipped; KEEP is the one the jukebox uses\n\n")
            fh.write("\n".join(sorted(dup_lines)) + ("\n" if dup_lines else ""))
    save_tags(a.tag_cache, tag_cache)

    # 4. sync DEST
    os.makedirs(dst_root, exist_ok=True)
    removed = added = 0
    for dirpath, _, files in os.walk(dst_root, topdown=False):
        for fn in files:
            q = os.path.join(dirpath, fn)
            if dirpath == dst_root and fn in KEEP:
                continue
            if fn == "fruitbox.db":
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
            link(p, q, a.mode)
            added += 1
    with open(marker, "w", encoding="utf-8") as fh:
        json.dump({"songs": total, "playlists": [l for l, _ in playlists]}, fh)
    print(f"\n{dst_root}: {added} added, {removed} removed")

    ini_changed = False
    if a.ini:
        ini_changed = update_ini(a.ini, ini_lines, all_label, include_all=not own_all)
        if ini_changed:
            print(f"updated MusicPath lines in {a.ini} (backup: {a.ini}.bak)")
    else:
        print("\nPaste these into [general] of fruitbox.ini, replacing the old MusicPath line(s):")
        print("\n".join(ini_lines))
        print(f"  MusicGroupIncludeAllSongs = {'No' if own_all else 'Yes'}")
        print(f"  MusicGroupAllSongsLabel = {all_label}")

    return 3 if (added or removed or ini_changed) else 0


if __name__ == "__main__":
    sys.exit(main())
