#!/usr/bin/env python3
"""
Build the jukebox's song list from a Windows music share, without copying music.

Scans SOURCE (the SMB share mounted on the Pi, e.g. /mnt/music) and picks every
song that is rated high enough OR carries a custom tag you chose. It then makes
DEST (e.g. ~/JukeboxLibrary) a mirror of just those songs, as symlinks to the
real files, plus each album's cover art:

    ~/JukeboxLibrary/Elvis Presley/Elvis Golden Records/01 Hound Dog.mp3
        -> /mnt/music/Elvis Presley/Elvis Golden Records/01 Hound Dog.mp3

Change a rating or tag on Windows and the next run adds or removes the link.
The share itself is never written to (mount it read-only).

Ratings understood (all turned into 0-5 stars):
  MP3   POPM (Windows Explorer / WMP / MediaMonkey / MusicBee), TXXX:RATING,
        TXXX:FMPS_Rating
  FLAC/OGG/Opus  RATING (1-5, 0-100) and FMPS_RATING (0.0-1.0)
  M4A   ----:com.apple.iTunes:RATING   (iTunes keeps ratings in its own
        library, not the file, so iTunes stars are NOT visible here)
  WMA   WM/SharedUserRating

Custom tag (--tag, repeatable):
  --tag grouping=Jukebox     a value of the field equals Jukebox
  --tag comment~jukebox      the field contains "jukebox"
  --tag JUKEBOX              the field exists and is not empty
Field names: grouping, comment, mood, genre, artist, album, title, or any
custom TXXX / Vorbis / MP4 freeform name, case-insensitive.

Run it from cron (see update-jukebox.sh). A tag cache keeps re-runs fast, so
only new or changed files are read over the network.

Needs: python3-mutagen   (sudo apt install python3-mutagen)
"""

import argparse
import json
import os
import re
import shutil
import sys

try:
    import mutagen
except ImportError:
    sys.exit("mutagen is missing: sudo apt install python3-mutagen")

# Same list as Fruitbox/fruitbox-setup/genre_library.py (Fruitbox v3 "Supported Media formats").
MEDIA_EXT = {
    ".aac", ".aiff", ".alac", ".flac", ".m4a", ".m4b", ".mp3", ".mid", ".mpa",
    ".ogg", ".opus", ".pcm", ".wav", ".wma",
    ".264", ".3gp", ".avi", ".divx", ".flv", ".m4v", ".mov", ".mp4", ".mkv",
    ".mpg", ".mpeg", ".ogv", ".wmv",
}
ART_EXT = {".jpg", ".jpeg", ".png", ".bmp"}
MARKER = ".jukebox_library"        # marks DEST as ours, so we may clean it
KEEP = {MARKER, "fruitbox.db"}     # never delete these from DEST
CACHE_VERSION = 3               # 3: artist/title/album cached for de-duplication

# ID3 frame -> friendly field name
ID3_NAMES = {
    "TIT1": "grouping", "GRP1": "grouping", "COMM": "comment", "TMOO": "mood",
    "TCON": "genre", "TPE1": "artist", "TPE2": "albumartist", "TALB": "album",
    "TIT2": "title", "TIT3": "subtitle", "TKEY": "key", "TCOM": "composer",
}
# MP4 atom -> friendly field name
MP4_NAMES = {
    "\xa9grp": "grouping", "\xa9cmt": "comment", "\xa9gen": "genre",
    "\xa9ART": "artist", "aART": "albumartist", "\xa9alb": "album",
    "\xa9nam": "title", "\xa9wrt": "composer",
}


# ---------------------------------------------------------------- tag reading

def _text(v):
    if isinstance(v, bytes):
        return v.decode("utf-8", "replace")
    if hasattr(v, "text"):                       # ID3 text frames
        return "\0".join(str(t) for t in v.text)
    if hasattr(v, "value"):                      # ASF attributes
        return str(v.value)
    return str(v)


def popm_stars(n):
    """POPM byte 0-255 -> stars. Covers WMP/Explorer (1,64,128,196,255),
    MediaMonkey and MusicBee scales."""
    if n <= 0:
        return 0.0
    for limit, stars in ((31, 1), (95, 2), (159, 3), (223, 4)):
        if n <= limit:
            return float(stars)
    return 5.0


def number_stars(text, fraction=False):
    """A rating written as text -> stars. Handles 0-1, 0-5, 0-10, 0-100, 0-255."""
    try:
        v = float(str(text).strip().split("\0")[0])
    except ValueError:
        return None
    if v <= 0:
        return 0.0
    if fraction or (v <= 1 and "." in str(text)):
        return round(v * 5, 2)
    if v <= 5:
        return v
    if v <= 10:
        return v / 2
    if v <= 100:
        return v / 20
    if v <= 255:
        return popm_stars(int(v))
    return None


def read_tags(path):
    """Return (stars or None, {field: [values]}) for one file."""
    try:
        f = mutagen.File(path)
    except Exception:
        return None, {}
    if f is None or not f.tags:
        return None, {}
    fields, ratings = {}, []

    def add(name, value):
        name = name.strip().lower()
        if name and value not in (None, ""):
            fields.setdefault(name, []).append(value)

    try:
        items = list(f.tags.items())
    except Exception:
        return None, {}
    for key, val in items:
        vals = val if isinstance(val, list) else [val]
        for v in vals:
            k = str(key)
            if k.startswith("POPM"):                         # ID3 rating
                ratings.append(popm_stars(getattr(v, "rating", 0)))
                continue
            if k.startswith("TXXX:"):
                add(k[5:], _text(v))
                continue
            if k.startswith("COMM"):
                add("comment", _text(v))
                continue
            if k[:4] in ID3_NAMES and (len(k) == 4 or k[4] == ":"):
                add(ID3_NAMES[k[:4]], _text(v))
                continue
            if k.startswith("----:"):                        # MP4 freeform
                add(k.rsplit(":", 1)[-1], _text(v))
                continue
            if k in MP4_NAMES:
                add(MP4_NAMES[k], _text(v))
                continue
            if k.startswith("WM/"):                          # WMA
                if k == "WM/SharedUserRating":
                    try:                                    # 1,25,50,75,99
                        n = int(_text(v))
                        ratings.append(0.0 if n <= 0 else min(5.0, 1 + n // 25))
                    except ValueError:
                        pass
                    continue
                add(k[3:], _text(v))
                continue
            add(k, _text(v))                                 # Vorbis, APE, ...

    for name in ("rating", "rating wmp", "rating mm"):
        for v in fields.get(name, []):
            s = number_stars(v)
            if s is not None:
                ratings.append(s)
    # FMPS_RATING (0.0-1.0) is what Andrew's library manager writes from Plex
    # (Plex 0-10 / 10). When a file has it, it wins over any older RATING/POPM
    # left behind by other programs.
    fmps = [s for s in (number_stars(v, fraction=True)
                        for v in fields.get("fmps_rating", [])) if s is not None]
    if fmps:
        return max(fmps), fields
    stars = max(ratings) if ratings else None
    return stars, fields


# ------------------------------------------------------------------ selection

class TagRule:
    def __init__(self, spec):
        m = re.match(r"\s*([^=~]+?)\s*(?:([=~])\s*(.*))?$", spec)
        if not m:
            raise ValueError(spec)
        self.field = m.group(1).lower()
        self.op = m.group(2)
        self.want = (m.group(3) or "").strip().lower()
        self.spec = spec

    def match(self, fields):
        for raw in fields.get(self.field, []):
            text = str(raw).lower()
            if self.op is None:
                if text.strip(" \0"):
                    return True
            elif self.op == "~":
                if self.want in text:
                    return True
            else:
                parts = [p.strip() for p in re.split(r"[;,/|\x00]", text)]
                if self.want in parts or text.strip() == self.want:
                    return True
        return False


# ------------------------------------------------------------- duplicates

# Tags kept in the cache for every file, so duplicates can be found.
META_FIELDS = ["artist", "albumartist", "title", "album", "compilation",
               "releasetype", "musicbrainz_albumtype"]

# "Live at ...", "(Live)", "- Live", "... Live", but not "Live Like You Were Dying"
LIVE_RE = re.compile(r"(\blive (at|in|from|on|and|for)\b|[\(\[]\s*live\b|-\s*live\b|"
                     r"\blive\s*[\)\]!]|^\s*live\s*$|\blive\s*$|\bunplugged\b|"
                     r"\bin concert\b|\bon stage\b|\bbootleg\b)", re.I)
HITS_RE = re.compile(r"\b(greatest|hits|best of|very best|essential|essentials|"
                     r"collection|anthology|gold|platinum|number ones|#1s|no\.? ?1s|"
                     r"definitive|ultimate|retrospective|icon|playlist|"
                     r"now that'?s what|various artists|soundtrack)\b", re.I)
SINGLE_RE = re.compile(r"(\bsingles?\b|\s-\s(single|ep)$|\((single|ep)\)$)", re.I)
TITLE_JUNK = re.compile(r"\s+-\s+.*\b(remaster(ed)?|live|version|edit|mix|mono|stereo|"
                        r"single|recorded|session)\b.*$", re.I)


def _first(fields, name):
    v = fields.get(name) or [""]
    return str(v[0]).split("\0")[0].strip()


def _norm(text):
    t = text.lower().replace("&", " and ")
    t = re.sub(r"[\(\[][^\)\]]*[\)\]]", " ", t)          # (Live), [Remastered 2011]
    t = re.sub(r"\b(feat|ft|featuring)\b.*$", " ", t)
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def song_key(fields):
    """(artist, title) that identifies the same song across albums, or None."""
    title = _first(fields, "title")
    artist = _first(fields, "artist") or _first(fields, "albumartist")
    if not title or not artist:
        return None
    title = TITLE_JUNK.sub("", title)
    artist = re.sub(r"^the\s+", "", _norm(artist))
    return (artist, _norm(title)) if _norm(title) else None


def version_kind(rel, fields):
    """0 studio album, 1 single/EP, 2 compilation/greatest hits, 3 live."""
    album = _first(fields, "album")
    rtype = (_first(fields, "releasetype") + " " + _first(fields, "musicbrainz_albumtype")).lower()
    title = _first(fields, "title")
    folder = os.path.dirname(rel)
    if "live" in rtype or LIVE_RE.search(album) or re.search(r"[\(\[-]\s*live\b", title, re.I):
        return 3
    if ("compilation" in rtype or _first(fields, "compilation") in ("1", "true")
            or HITS_RE.search(album)):
        return 2
    if "single" in rtype or re.search(r"\bep\b", rtype) or SINGLE_RE.search(album) \
            or SINGLE_RE.search(os.path.basename(folder)):
        return 1
    return 0


KIND_NAMES = ["album", "single", "compilation", "live"]


# -------------------------------------------------------------------- syncing

def same(src, dst, mode):
    try:
        if mode == "symlink":
            return os.path.islink(dst) and os.readlink(dst) == src
        s, d = os.stat(src), os.stat(dst)
        return s.st_size == d.st_size and int(s.st_mtime) == int(d.st_mtime)
    except OSError:
        return False


def place(src, dst, mode):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if mode == "symlink":
        os.symlink(src, dst)
    else:
        shutil.copy2(src, dst)


def load_cache(path, fields):
    try:
        with open(path, encoding="utf-8") as fh:
            c = json.load(fh)
        if c.get("version") == CACHE_VERSION and c.get("fields") == fields:
            return c["files"]
    except (OSError, ValueError, KeyError):
        pass
    return {}


def save_cache(path, fields, files):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump({"version": CACHE_VERSION, "fields": fields, "files": files}, fh)
    os.replace(tmp, path)


def main():
    home = os.path.expanduser("~")
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", default="/mnt/music",
                    help="the mounted Windows share (default /mnt/music)")
    ap.add_argument("--dest", default=os.path.join(home, "JukeboxLibrary"),
                    help="folder of links to build (default ~/JukeboxLibrary)")
    ap.add_argument("--min-stars", type=float, default=4,
                    help="pick songs rated at least this many stars; 0 turns rating "
                         "selection off (default 4)")
    ap.add_argument("--tag", action="append", default=[], metavar="RULE",
                    help="also pick songs matching FIELD=VALUE, FIELD~TEXT or FIELD "
                         "(repeatable)")
    ap.add_argument("--mode", choices=["symlink", "copy"], default="symlink",
                    help="symlink (default) or copy, if Fruitbox will not follow links")
    ap.add_argument("--cache", default=os.path.join(home, ".cache", "jukebox_library.json"),
                    help="tag cache file")
    ap.add_argument("--keep-free", type=float, default=8,
                    help="copy mode: stop if the Pi's drive would drop below this many "
                         "GB free (default 8; the OS shares the drive)")
    ap.add_argument("--max-remove", type=int, default=50,
                    help="refuse to remove more than this %% of existing songs in one "
                         "run, in case the share came up half-empty (default 50)")
    ap.add_argument("--force", action="store_true", help="ignore --max-remove")
    ap.add_argument("--no-mount-check", action="store_true",
                    help="allow a SOURCE that is not a mount point")
    ap.add_argument("--list", action="store_true", help="print each picked song")
    ap.add_argument("--keep-duplicates", action="store_true",
                    help="keep every copy of a song; by default only the best version is "
                         "kept (studio album over single, over greatest hits, over live)")
    ap.add_argument("--dup-report", default=os.path.join(home, "fruitbox", "duplicates.txt"),
                    help="where to write the list of skipped duplicates")
    ap.add_argument("--dry-run", action="store_true", help="report only, change nothing")
    a = ap.parse_args()

    try:
        rules = [TagRule(s) for s in a.tag]
    except ValueError as e:
        sys.exit(f"bad --tag rule: {e}")
    if a.min_stars <= 0 and not rules:
        sys.exit("nothing to select on: give --min-stars above 0 and/or --tag")

    src_root = os.path.abspath(a.source)
    dst_root = os.path.realpath(a.dest)
    if not os.path.isdir(src_root):
        sys.exit(f"source not found: {src_root} (is the share mounted?)")
    if not a.no_mount_check and not os.path.ismount(src_root):
        sys.exit(f"{src_root} is not mounted; leaving {dst_root} as it is "
                 "(use --no-mount-check for a local folder)")
    real_src = os.path.realpath(src_root)
    if dst_root == real_src or dst_root.startswith(real_src + os.sep) \
            or real_src.startswith(dst_root + os.sep):
        sys.exit("DEST and SOURCE must not contain each other")
    if os.path.isdir(dst_root) and os.listdir(dst_root) \
            and not os.path.exists(os.path.join(dst_root, MARKER)):
        sys.exit(f"{dst_root} is not empty and was not made by this script; pick another --dest")

    want_fields = sorted({r.field for r in rules} | set(META_FIELDS))
    cache = load_cache(a.cache, want_fields)
    new_cache, read, unreadable = {}, 0, 0

    # 1. scan the share (tags are read only for new or changed files)
    picked = []                                # (abs src path, rel path, why)
    songs = []                                 # every file: (path, rel, stars, fields)
    total = 0
    for dirpath, dirnames, files in os.walk(src_root):
        dirnames[:] = sorted(d for d in dirnames
                             if not d.startswith(".") and d not in ("$RECYCLE.BIN",
                                                                    "System Volume Information"))
        for fn in sorted(files):
            if os.path.splitext(fn)[1].lower() not in MEDIA_EXT:
                continue
            p = os.path.join(dirpath, fn)
            rel = os.path.relpath(p, src_root)
            total += 1
            try:
                st = os.stat(p)
            except OSError:
                unreadable += 1
                if rel in cache:
                    new_cache[rel] = cache[rel]
                continue
            sig = [st.st_size, int(st.st_mtime)]
            c = cache.get(rel)
            if c and c[0] == sig:
                stars, fields = c[1], c[2]
            else:
                stars, fields = read_tags(p)
                fields = {k: fields[k] for k in want_fields if k in fields}
                read += 1
            new_cache[rel] = [sig, stars, fields]
            why = []
            if a.min_stars > 0 and stars is not None and stars >= a.min_stars:
                why.append(f"{stars:g} stars")
            why += [r.spec for r in rules if r.match(fields)]
            songs.append((p, rel, stars, fields))
            if why:
                picked.append((p, rel, ", ".join(why)))
    if total == 0:
        sys.exit(f"no media files under {src_root}; leaving {dst_root} as it is")

    # 1b. one version per song: if a picked song also exists on other albums,
    #     keep the best version (studio album > single > greatest hits > live,
    #     then the higher rating), even if that version wasn't rated itself.
    dropped = []
    if not a.keep_duplicates:
        groups = {}
        for p, rel, stars, fields in songs:
            k = song_key(fields)
            if k:
                groups.setdefault(k, []).append((p, rel, stars, fields))
        by_rel = {rel: (p, why) for p, rel, why in picked}
        keep, done = [], set()
        for p, rel, why in picked:
            cache_fields = new_cache.get(rel)
            k = song_key(cache_fields[2]) if cache_fields else None
            versions = groups.get(k, []) if k else []
            if len(versions) < 2:
                keep.append((p, rel, why))
                continue
            if k in done:
                continue
            done.add(k)
            best = min(versions, key=lambda v: (version_kind(v[1], v[3]),
                                                -(v[2] or 0), v[1]))
            bwhy = by_rel[best[1]][1] if best[1] in by_rel else \
                f"best version of {rel} [{why}]"
            keep.append((best[0], best[1], bwhy))
            for v in versions:
                if v[1] != best[1] and v[1] in by_rel:
                    dropped.append((v[1], KIND_NAMES[version_kind(v[1], v[3])],
                                    best[1], KIND_NAMES[version_kind(best[1], best[3])]))
        picked = keep
        if a.dup_report and os.path.isdir(os.path.dirname(os.path.abspath(a.dup_report))) \
                and not a.dry_run:
            with open(a.dup_report, "w", encoding="utf-8") as fh:
                fh.write(f"{len(dropped)} duplicate songs skipped; KEEP shows the version the jukebox uses\n\n")
                for rel, kind, brel, bkind in sorted(dropped):
                    fh.write(f"SKIP [{kind}] {rel}\n  KEEP [{bkind}] {brel}\n")

    # 2. desired layout: DEST/<same path as on the share>, plus album art
    want = {}
    art_dirs = {}
    for p, rel, _ in picked:
        q = os.path.join(dst_root, rel)
        want[q] = p
        art_dirs[os.path.dirname(p)] = os.path.dirname(q)
    for sdir, ddir in art_dirs.items():
        try:
            names = os.listdir(sdir)
        except OSError:
            continue
        for fn in names:
            if os.path.splitext(fn)[1].lower() in ART_EXT:
                want[os.path.join(ddir, fn)] = os.path.join(sdir, fn)

    # 3. what would change
    existing = []
    if os.path.isdir(dst_root):
        for dirpath, _, files in os.walk(dst_root):
            existing += [os.path.join(dirpath, fn) for fn in files if fn not in KEEP]
    stale = [q for q in existing if q not in want or not same(want[q], q, a.mode)]
    have = set(existing) - set(stale)
    add = [q for q in want if q not in have]
    old_songs = sum(1 for q in existing if os.path.splitext(q)[1].lower() in MEDIA_EXT)
    gone_songs = sum(1 for q in stale if q not in want
                     and os.path.splitext(q)[1].lower() in MEDIA_EXT)

    print(f"{total} songs on the share ({read} tags read, {unreadable} unreadable), "
          f"{len(picked)} picked" + (f", {len(dropped)} duplicate versions skipped"
                                     if dropped else ""))
    if a.list:
        for _, rel, why in picked:
            print(f"  {rel}   [{why}]")
    print(f"{dst_root}: {len(add)} to add, {len(stale)} to remove")

    if old_songs >= 20 and gone_songs * 100 > old_songs * a.max_remove and not a.force:
        sys.exit(f"would remove {gone_songs} of {old_songs} songs, over the "
                 f"{a.max_remove}% limit; check the share, then re-run with --force")
    if a.mode == "copy":
        need = 0
        for q in add:
            try:
                need += os.stat(want[q]).st_size
            except OSError:
                pass
        freed = sum(os.lstat(q).st_size for q in stale if os.path.lexists(q))
        os.makedirs(os.path.dirname(dst_root) or "/", exist_ok=True)
        free = shutil.disk_usage(os.path.dirname(dst_root) or "/").free
        left = (free + freed - need) / 1e9
        print(f"copy mode: needs {need / 1e9:.1f} GB, {left:.1f} GB would stay free")
        if left < a.keep_free:
            sys.exit(f"not enough room: copying would leave {left:.1f} GB free, under "
                     f"--keep-free {a.keep_free:g} GB. Pick fewer songs or use symlinks.")
    if a.dry_run:
        return

    # 4. sync
    os.makedirs(dst_root, exist_ok=True)
    open(os.path.join(dst_root, MARKER), "a").close()
    for q in stale:
        os.remove(q)
    for dirpath, _, _ in os.walk(dst_root, topdown=False):
        if dirpath == dst_root:
            continue
        left = set(os.listdir(dirpath))
        if left <= {"fruitbox.db"}:
            for fn in left:
                os.remove(os.path.join(dirpath, fn))
            os.rmdir(dirpath)
    for q in add:
        place(want[q], q, a.mode)

    os.makedirs(os.path.dirname(os.path.abspath(a.cache)), exist_ok=True)
    save_cache(a.cache, want_fields, new_cache)
    # Exit code 3 tells update-jukebox.sh whether anything changed.
    sys.exit(3 if (add or stale) else 0)


if __name__ == "__main__":
    main()
