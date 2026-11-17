#!/usr/bin/env python3
"""
Tag reading and duplicate rules for the jukebox's music library.

Used by playlist_library.py (it is not run on its own):
  read_tags(path)        a song's rating (0-5 stars or None) and its tags
  song_key(fields)       (artist, title) that identifies the same song on several albums
  version_kind(rel, f)   0 studio album, 1 single/EP, 2 compilation/greatest hits, 3 live
  KIND_NAMES             names for those four, for the duplicates list

Tags understood: ID3 (MP3), Vorbis comments (FLAC/OGG/Opus), MP4 (M4A) and WMA.

Needs: python3-mutagen   (sudo apt install python3-mutagen)
"""

import os
import re
import sys

try:
    import mutagen
except ImportError:
    sys.exit("mutagen is missing: sudo apt install python3-mutagen")

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
    # FMPS_RATING (0.0-1.0) is what the music library manager writes from Plex
    # (Plex 0-10 / 10). When a file has it, it wins over any older RATING/POPM
    # left behind by other programs.
    fmps = [s for s in (number_stars(v, fraction=True)
                        for v in fields.get("fmps_rating", [])) if s is not None]
    if fmps:
        return max(fmps), fields
    stars = max(ratings) if ratings else None
    return stars, fields


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
