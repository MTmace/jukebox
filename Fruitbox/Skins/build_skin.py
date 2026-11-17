#!/usr/bin/env python3
"""Build the Firestar ultrawide Fruitbox v3 skin.

Generates fruitbox.cfg, the background and title strip images, and the status
text files into "./Firestar Ultrawide" (next to this script). Edit the constants below and
re-run to tweak the layout:  python3 build_skin.py

Needs Pillow (pip install pillow). Fonts are copied from Fruitbox's own skins
directory (FRUITBOX_SKINS), so run it where Fruitbox's stock skins exist, or
point FRUITBOX_SKINS at a checkout of github.com/chundermike/fruitbox-v3/skins.
"""
import os
import shutil
import sys

import status_screen  # second (status) display, see status_screen.py
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "Firestar Ultrawide")
FRUITBOX_SKINS = os.environ.get("FRUITBOX_SKINS", "/opt/fruitbox/skins")

# ---------------------------------------------------------------- layout ---
W, H = 3440, 1440                  # skin size; Fruitbox scales it to the panel
COLS, ROWS = 9, 8                  # 72 strips x 2 sides = 144 selections

# The glass was repainted (2026-11-08): the paint border is now 1.25"
# at the left/right edges of the 37" x 15" glass and 0.75" at the top/bottom,
# so the window is ~34.5" x 13.5", bigger than the 34" panel's ~31.3" x 13.1"
# picture. The whole picture shows, so the skin fills the screen. MASK_IN is how
# much of the picture the paint hides on each edge (0 now; the old 30" x 11"
# window hid about 0.67" at each side and 1.05" at the top and bottom).
# SLACK_IN keeps the panels and strips a little off the very edge of the screen.
PANEL_IN = (31.33, 13.11)          # visible picture of a 34" 21:9 panel (3440x1440, square pixels)
MASK_IN = dict(left=0.0, right=0.0, top=0.0, bottom=0.0)
SLACK_IN = 0.15
PX_PER_IN = W / PANEL_IN[0]        # ~110 px per inch
SAFE_X = round((MASK_IN["left"] + SLACK_IN) * PX_PER_IN)
SAFE_Y = round((MASK_IN["top"] + SLACK_IN) * PX_PER_IN)
SAFE_W = W - SAFE_X - round((MASK_IN["right"] + SLACK_IN) * PX_PER_IN)
SAFE_H = H - SAFE_Y - round((MASK_IN["bottom"] + SLACK_IN) * PX_PER_IN)

HEADER_H = 84                      # credits / Seeburg logo / genre, then the light bars
PANEL_H = 228                      # bottom status panels
SPEC_W = 300                       # spectrum wells at each end of the footer
SEL_W = 760                        # selection readout panel
VOL_PW = 110                       # volume panel between Selection and the right spectrum (2026-10-24)
VOL_BAR_W, VOL_SEGS = 56, 20       # its vertical LED bar; 20 = one segment per SongVolumeStep
                                   # of 5, so it always shows whole segments (2026-10-27)
PANEL_GAP = 24
SPEC_BARS = 8                      # bars per spectrum
# Page turn timed to the ~2 s page-turn sound, like Classic (speed 3, 28-tick ripple).
# Lower TURN_SPEED = slower turn; TURN_RIPPLE = ticks between first and last column.
TURN_SPEED = 50                     # tuned on the Pi 2026-10-16 (50 4 no)
# Strips show the shortened title strip_titles.py writes (25 chars + "...").
# Needs strip_titles.py run after genre_library.py, or strip titles are blank.
SHORT_TITLES = True
TURN_RIPPLE = 28
PAGE_TURN_WAV = "JBPTurn.wav"       # sounds copied from the Classic skin
BUTTON_WAV = "JBBPress.wav"
RECORD_WAV = "recpop.wav"          # record-start sound from the Carousel skin
# Pause between taking a song off the queue and the music starting, so the
# record-drop sound plays first. Carousel uses 100 ticks (about 1.7 s at 60 Hz).
SONG_LOAD_TIME = "1.7 seconds"
# Light bars under the logo twinkle (bars don't move). False = still bars.
LIGHT_BAR_ANIM = True
LIGHT_BAR_FRAMES = 60              # one loop; frames are lightbars/bars_NN.png
LIGHT_BAR_TICKS = 3                # video frames per animation frame (3 = 20 fps at 60 Hz)
LIGHT_BAR_PITCH = 26
GAP_X, GAP_Y, SECTION_GAP = 10, 8, 18
STRIP_W = (SAFE_W - (COLS - 1) * GAP_X) // COLS
GRID_Y = SAFE_Y + HEADER_H + SECTION_GAP
STRIP_H = (SAFE_Y + SAFE_H - PANEL_H - SECTION_GAP - GRID_Y - (ROWS - 1) * GAP_Y) // ROWS
PANEL_Y = SAFE_Y + SAFE_H - PANEL_H

# Number-only keypad, 3-digit codes like the real Firestar: hundreds 1-2, tens 0-7,
# ones 0-9 (100-179, 200-279). Each strip is a record like the real Seeburg:
# A side = 1xx on top, B side = 2xx below (100/200, 101/201, ...).
# "colrow" turns Fruitbox's whole order round: the FIRST SelectButtons line
# (hundreds) changes fastest, the last (ones) slowest, so the codes go 100, 200,
# 110, 210, ..., 170, 270, 101, 201, ... and each pair lands on one strip.
# ("rowcol" is the default: last line fastest, 100, 101, ... seen on the Pi.)
# 72 strips: tens 0-7 = row, ones 0-8 = column; codes ending in 9 have no song.
SELECT_DIGITS = ["12", "01234567", "0123456789"]
SELECT_SEQUENCE = "colrow"

# Title strip colour per genre tag. The first entry is the default strip.
# Keys must match the songs' genre *tag* text (Fruitbox matches it exactly).
# Strip colour follows the song's genre tag (exact text). Families follow
# the owner's genre list (genres.json from a music library manager): sub-genres and
# alternate names share their parent's colour. Unlisted tags get the default.
GENRE_FAMILIES = [
    # family            colour            other tags that share it
    ("Country",         (30, 115, 60),    ["Classic Country", "Contemporary Country", "Country Rock"]),
    ("Rock",            (196, 60, 20),    ["Soft Rock", "Classic Rock", "Hard Rock", "Alternative Rock",
                                           "Indie Rock", "Grunge", "Punk Rock", "Pop Rock", "80's Rock",
                                           "Psychedelic Rock"]),
    ("Oldies",          (178, 34, 34),    ["Rock & Roll", "Rock and Roll"]),
    ("Pop",             (25, 85, 165),    ["Indie Pop", "K-Pop"]),
    ("R&B",             (110, 40, 130),   ["Soul", "Funk"]),
    ("Jazz",            (20, 110, 120),   ["Vocal Jazz", "Swing", "Smooth Jazz"]),
    ("Blues",           (35, 55, 120),    []),
    ("Folk",            (120, 90, 40),    ["Bluegrass"]),
    ("Christian",       (150, 110, 20),   ["Gospel", "Contemporary Christian"]),
    ("Christmas",       (20, 95, 45),     ["Holiday"]),
    ("Metal",           (55, 55, 60),     ["Heavy Metal"]),
    ("Alternative",     (160, 40, 90),    []),
    ("Hip Hop",         (190, 90, 10),    ["Hip-Hop"]),
    ("Electronic",      (40, 80, 200),    ["Techno"]),
    ("Reggae",          (60, 130, 30),    []),
    ("Classical",       (90, 60, 50),     []),
    ("Soundtrack",      (70, 70, 110),    []),
    ("New Age",         (60, 120, 150),   []),
    ("Easy Listening",  (130, 80, 110),   []),
    ("Acoustic",        (140, 100, 50),   []),
    ("Singer Songwriter", (100, 70, 40),  ["Singer-songwriter", "Singer-song-writer", "Singer Song-writer"]),
    ("Ballad",          (150, 60, 100),   []),
    ("Other",           (90, 90, 95),     ["Instrumental"]),
]
DEFAULT_COLOUR = (178, 34, 34)       # Seeburg red

GENRE_COLOURS = [(None, DEFAULT_COLOUR)] + [
    (tag, col) for fam, col, others in GENRE_FAMILIES for tag in [fam] + others]
FAMILY_OF = {tag: fam for fam, _, others in GENRE_FAMILIES for tag in [fam] + others}

CREAM = (245, 238, 218)
INK = (28, 24, 22)
CHROME_HI, CHROME_LO = (236, 238, 242), (120, 126, 136)
# top bar: dark, like the cabinet trim around the glass (not grey)
BAR_HI, BAR_LO = (52, 48, 54), (6, 5, 7)
BAR_TEXT = (238, 230, 216)
# Firestar selector-panel palette (from a photo of the panel): glowing red, orange
# and yellow bars on black, a lime-green "1st DIGIT" box.
FS_RED = (232, 34, 58)
FS_ORANGE = (255, 112, 24)
FS_YELLOW = (255, 210, 20)
FS_LIME = (176, 230, 40)
FIRE = FS_RED
AMBER = FS_YELLOW
# calculator-style select code: lit segments over dim "888" segments
LED_ON = (255, 58, 48)
LED_GHOST = (58, 14, 12)
LOGO_PNG = "seeburg_logo.png"      # black-on-transparent Seeburg wordmark

FONTS = [  # (file in FRUITBOX_SKINS, size) -> font numbers 1..n in the cfg
    ("SB-M100/dvsansbc.ttf", 23),   # 1 strip song titles
    ("Seeburg/Anton-Regular.ttf", 22),  # 2 strip artist band
    ("Seeburg/Anton-Regular.ttf", 20),  # 3 strip select codes
    ("Seeburg/Anton-Regular.ttf", 44),  # 4 panel headings
    ("SB-M100/dvsansbc.ttf", 46),   # 5 now playing title
    ("SB-M100/dvsansc.ttf", 34),    # 6 now playing artist / coming up
    ("technology-mono.ttf", 168),  # 7 select code / clock readout (7-segment)
    ("Seeburg/Anton-Regular.ttf", 40),  # 8 header text (status screen)
    # 4-8 are shared with the status screen; the main screen's smaller
    # panel text (to fit the glass window) uses these:
    ("Seeburg/Anton-Regular.ttf", 36),  # 9 panel headings
    ("SB-M100/dvsansbc.ttf", 40),   # 10 now playing title
    ("SB-M100/dvsansc.ttf", 28),    # 11 now playing artist / coming up
    ("technology-mono.ttf", 152),  # 12 select code readout (7-segment)
    ("Seeburg/Anton-Regular.ttf", 34),  # 13 header text
    # 14: COMING UP title. Fruitbox draws fonts at ~0.8x Pillow's size, so 45 here
    # matches the NOW PLAYING / SELECTION titles baked in at 36 (font 9)
    ("Seeburg/Anton-Regular.ttf", 45),  # 14 coming up title
]


def strip_positions():
    total_w = COLS * STRIP_W + (COLS - 1) * GAP_X
    x0 = SAFE_X + (SAFE_W - total_w) // 2
    # Order matters: Fruitbox hands out select codes in [title strip] order.
    # Going down each column first numbers the strips down each column:
    # column 1 = 100/200 ... 170/270, column 2 = 101/201 ... 171/271, ...
    # column 9 = 108/208 ... 178/278 (A side on top, B side below).
    for c in range(COLS):
        for r in range(ROWS):
            yield x0 + c * (STRIP_W + GAP_X), GRID_Y + r * (STRIP_H + GAP_Y)


def grid_box():
    total_w = COLS * STRIP_W + (COLS - 1) * GAP_X
    x0 = SAFE_X + (SAFE_W - total_w) // 2
    y1 = GRID_Y + ROWS * STRIP_H + (ROWS - 1) * GAP_Y
    return x0, GRID_Y, x0 + total_w, y1


def font_file(f):
    """Fonts kept next to this script win over Fruitbox's stock skins.

    technology-mono.ttf is Carousel/technology.bold.ttf with every digit (and the
    dash) the same width as an 8, and 1/3/4/7 moved right to sit on the 8's
    segments, so typed codes line up with the dim "888" behind them.
    """
    local = os.path.join(HERE, f)
    return local if os.path.exists(local) else os.path.join(FRUITBOX_SKINS, f)


def font(i, scale=1.0):
    f, s = FONTS[i - 1]
    return ImageFont.truetype(font_file(f), int(s * scale))


# ----------------------------------------------------------------- images ---
def vgrad(w, h, top, bot):
    im = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(im)
    for y in range(h):
        t = y / max(1, h - 1)
        d.line([(0, y), (w, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(top, bot)))
    return im


def chrome_bar(w, h):
    im = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(im)
    for y in range(h):
        t = y / max(1, h - 1)
        # bright band a third of the way down, like polished trim
        k = 1 - min(1, abs(t - 0.33) * 2.2)
        c = tuple(int(lo + (hi - lo) * k) for hi, lo in zip(BAR_HI, BAR_LO))
        d.line([(0, y), (w, y)], fill=c)
    return im


def chrome_face(size):
    """Bright silver gradient for lettering on the dark bar."""
    w, h = size
    im = Image.new("RGBA", (w, h))
    d = ImageDraw.Draw(im)
    for y in range(h):
        t = y / max(1, h - 1)
        k = 1 - min(1, abs(t - 0.3) * 1.6)
        c = tuple(int(lo + (hi - lo) * k) for hi, lo in zip((255, 255, 255), (150, 156, 166)))
        d.line([(0, y), (w, y)], fill=c + (255,))
    return im


def light_bars(im, box, pitch=LIGHT_BAR_PITCH, bar=16, level=None):
    """Slanted glowing bars, red/orange/yellow, like the selector panel.

    level(i) gives a brightness for bar i (1.0 = normal); used for the twinkle.
    """
    x0, y0, x1, y1 = box
    g = Image.new("RGBA", im.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(g)
    cols = (FS_RED, FS_ORANGE, FS_YELLOW)
    slant = (y1 - y0) // 2
    for i, x in enumerate(range(x0 - pitch, x1 + pitch, pitch)):
        c = cols[i % 3]
        if level:
            k = level(i)
            # brighter than normal also whitens a little, like a lamp flaring
            c = tuple(min(255, int(v * min(k, 1.0) + (255 - v) * max(0.0, k - 1.0))) for v in c)
        gd.polygon([(x + slant, y0), (x + slant + bar, y0), (x + bar, y1), (x, y1)], fill=c + (255,))
    glow = g.filter(ImageFilter.GaussianBlur(5))
    im.paste(glow, (0, 0), glow)
    im.paste(g, (0, 0), g)


def light_bar_box():
    """(x0, y0, x1, y1) of the light-bar strip under the header, and the bars inside it."""
    hy1 = SAFE_Y + HEADER_H
    by0 = hy1 - 14
    return (0, by0 - 3, W, hy1), (0, by0, W, hy1 - 2)


def make_light_bar_frames():
    """Frames for the twinkling light bars: same bars as the background, each
    one now and then flaring brighter and fading back, at its own random time.
    The bars never move. Loops seamlessly every LIGHT_BAR_FRAMES frames."""
    import math
    import random
    (sx0, sy0, sx1, sy1), bars = light_bar_box()
    d = os.path.join(OUT, "lightbars")
    os.makedirs(d, exist_ok=True)
    for old in os.listdir(d):
        os.remove(os.path.join(d, old))
    n = LIGHT_BAR_FRAMES
    count = W // LIGHT_BAR_PITCH + 3
    rnd = random.Random(1959)               # fixed seed: same twinkle every build
    # each bar twinkles once or twice per loop, at a random moment
    plan = [(rnd.choice((1, 1, 1, 2)), rnd.random()) for _ in range(count)]
    for f in range(n):
        t = f / n
        def level(i, t=t):
            times, phase = plan[i]
            p = (t * times + phase) % 1.0
            flare = math.cos((p - 0.5) * math.pi * 12) if abs(p - 0.5) < 1 / 24 else 0.0
            return 0.88 + 0.5 * flare             # dim a touch, flare to bright
        im = Image.new("RGB", (W, H), (6, 4, 6))
        light_bars(im, bars, level=level)
        im.crop((sx0, sy0, sx1, sy1)).save(os.path.join(d, f"bars_{f:02d}.png"), optimize=True)



def rounded_panel(im, box, r=18, fill=(14, 12, 16), edge=CHROME_LO, glow=None):
    d = ImageDraw.Draw(im)
    if glow:
        g = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ImageDraw.Draw(g).rounded_rectangle(box, r, outline=glow + (200,), width=10)
        im.paste(g.filter(ImageFilter.GaussianBlur(14)), (0, 0), g.filter(ImageFilter.GaussianBlur(14)))
    d.rounded_rectangle(box, r, fill=fill, outline=edge, width=4)
    d.rounded_rectangle((box[0] + 6, box[1] + 6, box[2] - 6, box[3] - 6), r - 6, outline=(60, 60, 70), width=2)


def make_background():
    im = vgrad(W, H, (30, 8, 6), (8, 6, 10))
    d = ImageDraw.Draw(im)

    # warm "firelight" glow behind the strip rack
    gx0, gy0, gx1, gy1 = grid_box()
    glow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(glow).rounded_rectangle((gx0 - 10, gy0 - 10, gx1 + 10, gy1 + 10), 30, fill=150)
    glow = glow.filter(ImageFilter.GaussianBlur(40))
    im.paste(Image.new("RGB", (W, H), (120, 30, 8)), (0, 0), glow)

    # rack: dark tray with chrome rim
    d.rounded_rectangle((gx0 - 12, gy0 - 10, gx1 + 12, gy1 + 10), 12, fill=(18, 14, 14), outline=CHROME_LO, width=4)
    # thin chrome dividers between columns, like the program holder
    for c in range(1, COLS):
        x = gx0 + c * (STRIP_W + GAP_X) - GAP_X // 2
        d.line([(x, gy0 - 4), (x, gy1 + 4)], fill=(70, 70, 78), width=2)

    # header: chrome bar (runs up under the paint) with the Seeburg logo in
    # the middle, then a row of glowing red/orange/yellow bars like the
    # Firestar's selector panel
    (_, sy0, _, hy1), bars = light_bar_box()
    by0 = bars[1]
    im.paste(chrome_bar(W, sy0), (0, 0))
    d.rectangle((0, sy0, W, hy1), fill=(6, 4, 6))
    light_bars(im, bars)   # still copy; the animated frames draw over it
    logo = Image.open(os.path.join(HERE, LOGO_PNG)).convert("RGBA")
    lh = by0 - 3 - SAFE_Y - 8
    logo = logo.resize((int(logo.width * lh / logo.height), lh), Image.LANCZOS)
    lx, ly = (W - logo.width) // 2, SAFE_Y + 4
    # polished-chrome lettering on the dark bar, with a faint red glow
    a = logo.getchannel("A")
    glow = Image.new("RGBA", logo.size, FS_RED + (0,))
    glow.putalpha(a.filter(ImageFilter.GaussianBlur(6)).point(lambda v: v * 0.6))
    im.paste(glow, (lx, ly), glow)
    face = chrome_face(logo.size)
    face.putalpha(a)
    im.paste(face, (lx, ly), face)

    # bottom panels
    np_box, sel_box, cu_box = panel_boxes()
    rounded_panel(im, np_box, glow=FIRE)
    rounded_panel(im, sel_box, glow=AMBER)
    rounded_panel(im, cu_box, glow=FIRE)
    rounded_panel(im, vol_panel(), glow=FIRE)
    for box in spectrum_boxes():
        rounded_panel(im, box, fill=(6, 6, 8), glow=FIRE)
    # artwork frame
    ax, ay, aw = art_box()
    d.rectangle((ax - 6, ay - 6, ax + aw + 5, ay + aw + 5), fill=(40, 40, 46), outline=CHROME_HI, width=3)

    # static headings (baked in, so they never depend on status timing)
    hf = font(9)
    d.text((ax + aw + 32, np_box[1] + 12), "NOW PLAYING", font=hf, fill=FIRE)
    tw = d.textlength("SELECTION", font=hf)
    # same font and colour as NOW PLAYING and COMING UP
    d.text(((sel_box[0] + sel_box[2] - tw) / 2, sel_box[1] + 12), "SELECTION", font=hf, fill=FIRE)
    vp = vol_panel()
    tw = d.textlength("VOL", font=hf)
    d.text(((vp[0] + vp[2] - tw) / 2, vp[1] + 12), "VOL", font=hf, fill=FIRE)
    bx0, by0, _, _ = vol_bar_box()             # unlit segments; the lit bar is clipped over them
    ghost = vol_bar_image(False)
    im.paste(ghost, (bx0, by0), ghost)
    vol_bar_image(True).save(os.path.join(OUT, "vol_bar_main.png"))
    # readout window behind the select code: black glass with a soft red
    # glow round the edge, like the lit panels on the Firestar
    sx0, sy0, sx1, sy1 = code_box()
    g = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(g).rounded_rectangle((sx0, sy0, sx1, sy1), 12, outline=FS_RED + (230,), width=6)
    g = g.filter(ImageFilter.GaussianBlur(6))
    im.paste(g, (0, 0), g)
    d.rounded_rectangle((sx0, sy0, sx1, sy1), 12, fill=(6, 2, 3), outline=FS_RED, width=2)
    d.rounded_rectangle((sx0 + 5, sy0 + 5, sx1 - 5, sy1 - 5), 8, outline=(48, 10, 12), width=1)

    im.save(os.path.join(OUT, "background.png"), optimize=True)
    # empty cover art frame, drawn over the last song's artwork once nothing is playing
    im.crop((ax, ay, ax + aw, ay + aw)).save(os.path.join(OUT, "art_blank.png"), optimize=True)


def spectrum_boxes():
    """Spectrum wells at the far left and right of the footer."""
    gx0, _, gx1, _ = grid_box()
    return ((gx0, PANEL_Y, gx0 + SPEC_W, PANEL_Y + PANEL_H),
            (gx1 - SPEC_W, PANEL_Y, gx1, PANEL_Y + PANEL_H))


def panel_boxes():
    gx0, _, gx1, _ = grid_box()
    gx0 += SPEC_W + PANEL_GAP
    gx1 -= SPEC_W + PANEL_GAP
    side_w = (gx1 - gx0 - SEL_W - 2 * PANEL_GAP) // 2
    # Coming Up | Now Playing | Selection, the same order as the second screen,
    # with Now Playing centred on the screen (2026-10-24)
    edge_w = (gx1 - gx0 - side_w - 2 * PANEL_GAP) // 2
    cu_box = (gx0, PANEL_Y, gx0 + edge_w, PANEL_Y + PANEL_H)
    np_box = (cu_box[2] + PANEL_GAP, PANEL_Y, gx1 - edge_w - PANEL_GAP, PANEL_Y + PANEL_H)
    sel_box = (gx1 - edge_w, PANEL_Y, gx1 - VOL_PW - PANEL_GAP, PANEL_Y + PANEL_H)
    return np_box, sel_box, cu_box


def vol_panel():
    """Volume panel at the right end of the footer, beside the right spectrum."""
    gx1 = grid_box()[2] - SPEC_W - PANEL_GAP
    return gx1 - VOL_PW, PANEL_Y, gx1, PANEL_Y + PANEL_H


def vol_bar_box():
    """Vertical volume bar, centred in the volume panel under the heading."""
    x0, y0, x1, y1 = vol_panel()
    cx = (x0 + x1) // 2
    return cx - VOL_BAR_W // 2, y0 + 62, cx + VOL_BAR_W // 2, y1 - 18


def vol_bar_image(lit):
    """LED segments, lime at the bottom to red at the top, lit or ghosted."""
    bx0, by0, bx1, by1 = vol_bar_box()
    w, h = bx1 - bx0, by1 - by0
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    seg = h / VOL_SEGS
    for i in range(VOL_SEGS):          # i = 0 is the bottom segment
        t = i / (VOL_SEGS - 1)
        c = FS_LIME if t < 0.6 else FS_YELLOW if t < 0.85 else FS_RED
        if not lit:
            c = tuple(v // 5 for v in c)
        d.rounded_rectangle((2, round(h - (i + 1) * seg) + 1, w - 3, h - round(i * seg) - 1), 1, fill=c + (255,))
    return im


ART_CONTENTS = ("${IF_SONG_PLAYING}${NOW_PLAYING_ARTWORK}\\n"
                "${IF_SONG_PLAYING}${UNDRAW_BITMAP}\\n"
                "${IF_NOT_SONG_PLAYING}${DRAW_BITMAP}")


def art_box():
    np_box = panel_boxes()[0]
    return np_box[0] + 22, np_box[1] + 22, PANEL_H - 44


# Select code's vertical offset in its window, measured in a test render so the
# 7-segment digits sit with equal space above and below.
READOUT_DY = 5


def code_box():
    sel = panel_boxes()[1]
    return sel[0] + 40, sel[1] + 62, sel[2] - 40, sel[1] + 170


def make_strip(colour, path):
    """Paper title strip: A side / artist band / B side, codes on the left."""
    s = 4  # supersample for crisp edges
    w, h = STRIP_W * s, STRIP_H * s
    im = Image.new("RGB", (w, h), CREAM)
    d = ImageDraw.Draw(im)
    band_y0, band_y1 = int(h * 0.37), int(h * 0.63)
    d.rectangle((0, band_y0, w, band_y1), fill=colour)
    # pin-stripes either side of the band and along the edges
    for y in (band_y0 - 5 * s, band_y1 + 4 * s):
        d.rectangle((10 * s, y, w - 10 * s, y + s), fill=colour)
    d.rectangle((0, 0, w, 3 * s), fill=colour)
    d.rectangle((0, h - 3 * s, w, h), fill=colour)
    # code tab on the left of each song line
    d.line([(44 * s, 6 * s), (44 * s, band_y0 - 7 * s)], fill=colour, width=s)
    d.line([(44 * s, band_y1 + 7 * s), (44 * s, h - 6 * s)], fill=colour, width=s)
    d.rectangle((0, 0, w - 1, h - 1), outline=(150, 140, 120), width=s)
    im = im.resize((STRIP_W, STRIP_H), Image.LANCZOS)
    im.save(path, optimize=True)


def make_spectrum_bar():
    """One rainbow bar (red top, blue bottom) with clear margins, like the Classic skin."""
    stops = [(255, 0, 0), (255, 255, 0), (0, 255, 0), (0, 255, 255), (0, 0, 255), (60, 0, 255)]
    w, h, margin = 64, 256, 8
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for y in range(h):
        t = y / (h - 1) * (len(stops) - 1)
        i = min(int(t), len(stops) - 2)
        f = t - i
        c = tuple(round(stops[i][k] + (stops[i + 1][k] - stops[i][k]) * f) for k in range(3))
        d.line([(margin, y), (w - margin - 1, y)], fill=c + (255,))
    im.save(os.path.join(OUT, "spectrum.png"))


# -------------------------------------------------------------------- cfg ---
# Now Playing title (2026-10-16): the short title ("...") is for the strips
# only. Screen 1 squeezes the full title to fit; screen 2 scrolls it when it's too
# wide. Scrolling moves one step per status timer tick, so that box ticks every
# frame (a 1 second tick made any speed crawl). Speed 3 was chosen on the Pi.
TITLE_SCROLL = 3
TITLE_TICK = "TimerTickPeriod = 1"


def text(fontno, rgb, align="centre", caps="false", mode=-1, quoted="false", off=(0, 0), maxw=0, a=255):
    r, g, b = rgb
    return f"{fontno} {r} {g} {b} {a} {align} {caps} {mode} {quoted} {off[0]} {off[1]} {maxw}"


def genre_file(g):
    """One strip image per colour family; every tag in the family points at it."""
    if g is None:
        return "strip_default.png"
    fam = FAMILY_OF.get(g, g)
    return "strip_" + "".join(ch.lower() if ch.isalnum() else "_" for ch in fam).strip("_") + ".png"


def write_cfg():
    np_box, sel_box, cu_box = panel_boxes()
    ax, ay, aw = art_box()
    cx0, cy0, cx1, cy1 = code_box()
    L = []
    a = L.append
    a("# Firestar ultrawide skin for Fruitbox v3 (generated by build_skin.py)")
    a("# Seeburg USC2 Firestar, 34\" 21:9 panel under the flat glass.")
    a("# Fruitbox scales the skin to the screen, so a 2560x1080 panel works too.")
    a("")
    a("[general]")
    a("SkinName = Firestar Ultrawide")
    a(f"SkinDescription = {COLS * ROWS * 2}-selection Seeburg-style rack for a 34in 21:9 screen")
    a("SkinVersion = 1.0")
    a("NoDuplicates = Yes")          # a song already queued or playing can't be picked again (2026-10-17)
    a(f"SkinSize = 1 {W} {H}")
    # second (status) display: size here, objects at the end of the file
    L.extend(status_screen.general_lines())
    a("")
    a("# No MusicPath here on purpose: fruitbox.ini owns the music and the")
    a("# per-genre MusicGroups that the genre button cycles through.")
    # Playlists era (2026-11-04): songs in Artist -> Album -> Track order, the same order the
    # PlexMediaToolkit Jukebox page sorts the playlist files in. Fruitbox applies the sorts in turn,
    # so the LAST line is the main one (LeftSort/RightSort also jump by the last one's first letter).
    a("SortSongsBy = TrackNumber")
    a("SortSongsBy = Album")
    a("SortSongsBy = Artist")
    a("")
    a("# Number-only keypad: 3-digit codes, A side 1xx / B side 2xx on each strip")
    a(f"SelectButtonsSequence = {SELECT_SEQUENCE}")
    for digits in SELECT_DIGITS:
        a(f"SelectButtons = {digits}")
    a("AutoSelect = Yes")
    a("SelectTimeout = 10 seconds")
    a("SelectHoldTimeout = 3 seconds")
    a("HideInvalidStripCodes = Yes")
    a("TitleStripAutoTurnTime = 2 minutes")
    a("")
    a("SongsPerTitleStrip = 2")
    a("PairSongs = Dual")
    a(f"TitleStripSize = {STRIP_W} {STRIP_H}")
    for g, _ in GENRE_COLOURS:
        a(f"TitleStripBackground = {genre_file(g)}" + (f" {g}" if g else ""))
    a(f"TitleStripMoveStyle = {TURN_SPEED} 4 no")
    a("")
    if SHORT_TITLES:
        a("# Strip titles come from the Custom field, filled with a shortened title")
        a("# by strip_titles.py (run after genre_library.py). Full titles elsewhere.")
        a("SongDescription = ${CUSTOM_TAG}")
        a("PairedSongDescription = ${PAIRED_CUSTOM_TAG}")
    else:
        a("SongDescription = ${SONG_TITLE}")
        a("PairedSongDescription = ${PAIRED_SONG_TITLE}")
    a("ArtistDescription = ${SONG_ARTIST} / ${PAIRED_SONG_ARTIST}")
    a("MatchedArtistDescription = ${SONG_ARTIST}")
    a("ExtraDescription = ${STRIP_CODE}")
    a("ExtraDescription = ${PAIRED_STRIP_CODE}")
    inner = STRIP_W - 60
    a("SongText = " + text(1, INK, maxw=inner, off=(20, 0)))
    a("PairedSongText = " + text(1, INK, maxw=inner, off=(20, 0)))
    a("ArtistText = " + text(2, (255, 255, 255), caps="true", maxw=STRIP_W - 24))
    a("ExtraText = " + text(3, INK, align="left", off=(8, round(STRIP_H * 0.05))))
    a("ExtraText = " + text(3, INK, align="left", off=(8, round(STRIP_H * 0.66))))
    a("")
    a(f"SongLoadTime = {SONG_LOAD_TIME}")
    a("SongUnloadTime = 0")
    a("NowPlayingArtworkMode = auto")
    a("")
    a("# Attract mode: list genres here to make the AttractMode button cycle")
    a("# Off -> each genre -> Any. Leave commented for a plain on/off toggle.")
    a("#AttractModeGenre = Rock & Roll")
    a("#AttractModeGenre = Soul")
    a("")
    a("[fonts]")
    for f, sz in FONTS:
        a(f"File = {os.path.basename(f)} {sz}")
    a("")
    a("# ---- background (drawn first) ----")
    a("[bitmap]")
    a("File = background.png")
    a("Position = 0 0")
    a(f"Size = {W} {H}")
    a("")
    a("# ---- title strips: down each column, left to right ----")
    for i, (x, y) in enumerate(strip_positions()):
        a("[title strip]")
        a(f"Position = {x} {y}")
        a(f"MoveDelay = {(i // ROWS) * TURN_RIPPLE // (COLS - 1) + (i % ROWS)}")
        a("")

    a("# ---- header: credits (left) and genre (right) ----")
    a("[status]")
    a(f"Position = {SAFE_X + 20} {SAFE_Y + 8}")
    a("Size = 900 50")
    a("Text = " + text(13, BAR_TEXT, align="left"))
    a("Contents = credits.txt")
    a("")
    a("[status]")
    a(f"Position = {SAFE_X + SAFE_W - 920} {SAFE_Y + 8}")
    a("Size = 900 50")
    a("Text = " + text(13, BAR_TEXT, align="right"))
    a("Contents = genre.txt")
    a("")

    a("# ---- now playing ----")
    a("[status]")
    a(f"Position = {ax} {ay}")
    a(f"Size = {aw} {aw}")
    # Fruitbox leaves the last cover up after the song ends, so cover it with the
    # empty frame (art_blank.png) whenever nothing is playing.
    a("Bitmap = art_blank.png")
    a("Contents = \"" + ART_CONTENTS + "\"")
    a("")
    tx = ax + aw + 32
    tw = np_box[2] - tx - 26
    a("[status]")
    a(f"Position = {tx} {np_box[1] + 66}")
    a(f"Size = {tw} 54")
    a("Text = " + text(10, (255, 244, 225), align="left", mode=-1, maxw=tw))
    a("Contents = \"${IF_SONG_PLAYING}${NOW_PLAYING_TITLE}${ELSE}Make your selection\"")
    a("")
    a("[status]")
    a(f"Position = {tx} {np_box[1] + 124}")
    a(f"Size = {tw} 90")
    a("Text = " + text(11, (210, 200, 190), align="left", mode=-1, maxw=tw))
    a("LineSpacing = 8")
    a("Contents = now_playing.txt")
    a("")

    a("# ---- selection readout ----")
    # Left-aligned at the same spot as the "888", so each typed digit (even a
    # part-typed code) lands on its own unlit 8.
    # Fruitbox draws a TTF at about 0.8x the size Pillow does (measured in a
    # test render), so scale the width before centring it in the window.
    dw = int(font(12, scale=0.8).getlength("888")) + 1
    dx = cx0 + (cx1 - cx0 - dw) // 2
    a("[status]")
    a(f"Position = {dx} {cy0 + READOUT_DY}")
    a(f"Size = {dw + 20} {cy1 - cy0 - 6}")
    a("Text = " + text(12, LED_GHOST, align="left"))
    a("Contents = select_ghost.txt")
    a("")
    a("[status]")
    a(f"Position = {dx} {cy0 + READOUT_DY}")
    a(f"Size = {dw + 20} {cy1 - cy0 - 6}")
    a("Text = " + text(12, LED_ON, align="left"))
    a("Contents = \"${SELECT_CODE}\"")
    a("")
    a("[status]")
    a(f"Position = {sel_box[0]} {sel_box[3] - 50}")
    a(f"Size = {sel_box[2] - sel_box[0]} 40")
    a("Text = " + text(11, (210, 200, 190)))
    a("Contents = select_hint.txt")
    a("")

    a("# ---- volume: vertical LED bar that fills upward with ${VOLUME} (no number, 2026-10-24) ----")
    bx0, by0, bx1, by1 = vol_bar_box()
    a("[bitmap]")
    a(f"Position = {bx0} {by0}")
    a(f"Size = {bx1 - bx0} {by1 - by0}")
    a("File = vol_bar_main.png")
    # Clip is in screen pixels: its top moves up from the bar's bottom as its height grows
    a(f"Clip = {bx0} {by1 - 1} [{by0} ${{VOLUME}}] {bx1 - bx0} 1 [{by1 - by0} ${{VOLUME}}]")
    a("")

    a("# ---- coming up ----")
    a("[status]")
    a(f"Position = {cu_box[0] + 26} {cu_box[1] + 12}")
    a(f"Size = {cu_box[2] - cu_box[0] - 52} 56")
    a("Text = " + text(14, FIRE, align="left"))
    a("Contents = coming_up_title.txt")
    a("")
    a("[status]")
    a(f"Position = {cu_box[0] + 26} {cu_box[1] + 70}")
    a(f"Size = {cu_box[2] - cu_box[0] - 52} 146")
    a("Text = " + text(11, (210, 200, 190), align="left", mode=-1, maxw=cu_box[2] - cu_box[0] - 52))
    a("LineSpacing = 4")
    a("Contents = coming_up.txt")
    a("")

    a("# ---- spectrum analysers at each end of the footer (live, from the music) ----")
    for (x0, y0, x1, y1), flip, chan, bands in zip(
        spectrum_boxes(), ("yes", "no"), ("left", "right"),
        ((0, 2, 4, 6, 9, 12, 15, 18), (1, 3, 5, 7, 10, 13, 16, 19))):
        a("[spectrum]")
        a("Bitmap = spectrum.png")
        a("Mode = scaled")
        a(f"Position = {x0 + 16} {y0 + 16}")
        a(f"Size = {x1 - x0 - 32} {y1 - y0 - 32}")
        a(f"HorizontalFlip = {flip}")
        a(f"Channel = {chan}")
        a("Decay = 3")
        for b in bands[:SPEC_BARS]:
            a(f"Band = {b} 1.0 0 0")
        a("")

    if LIGHT_BAR_ANIM:
        (sx0, sy0, sx1, sy1), _ = light_bar_box()
        a("# ---- animated light bars under the logo (frames in lightbars/) ----")
        a("[status]")
        a(f"Position = {sx0} {sy0}")
        a(f"Size = {sx1 - sx0} {sy1 - sy0}")
        a(f"TimerTickPeriod = {LIGHT_BAR_TICKS}")
        for f in range(LIGHT_BAR_FRAMES):
            a(f"Bitmap = lightbars/bars_{f:02d}.png")
        a('Initial = "${DRAW_BITMAP}"')
        a('Contents = "${IF_TIMER_TICK}${DRAW_BITMAP}"')
        a("")

    a("# ---- navigation sounds (from Fruitbox's Classic skin) ----")
    a("[status]")
    a("Contents = page_turn.txt")
    a(f"Sound = {PAGE_TURN_WAV} 50")
    a("")
    a("[status]")
    a("Contents = button_press.txt")
    a(f"Sound = {BUTTON_WAV} 50")
    a("")
    a("# record drop / needle sound as each song loads (from Fruitbox's Carousel skin)")
    a("[status]")
    a("Contents = record_start.txt")
    a(f"Sound = {RECORD_WAV} 100")
    a("")
    a("# ---- jukebox state for the cabinet lights: not drawn (no Size), written to a")
    a("# file in memory that cabinet-lights/jukebox-bridge.py reads to pick WLED presets ----")
    a("[status]")
    a("Position = 0 0")
    a("TimerTickPeriod = 1 second")
    a("Contents = lights_state.txt")
    a("Output = /dev/shm/jukebox_state.txt")
    a("")

    a("# ---- second display (status screen) goes below this line ----")
    a("")
    L.extend(status_screen.cfg_lines(sys.modules[__name__]))
    # read by status-page/jukebox-status.py (status web page); keep it LAST
    a("")
    a("# JUKEBOX: hidden status box for the status page (status-page/install-status.sh).")
    a("# Keep it LAST in the file.")
    a("[status]")
    a("Position = 0 0")
    a("TimerTickPeriod = 1 second")
    a("Contents = jukebox_status.txt")
    a("Output = /dev/shm/jukebox_fruitbox.txt")
    with open(os.path.join(OUT, "fruitbox.cfg"), "w") as fh:
        fh.write("\n".join(L))


STATUS_FILES = {
    "credits.txt": "${IF_FREEPLAY}FREE PLAY${ELSE}CREDITS ${CREDITS}\n",
    "select_ghost.txt": "${IF_FREEPLAY}888${ELSE}888\n",  # unlit "888" behind the code; needs a ${...} or Fruitbox draws a black box
    "genre.txt": "${IF_ATTRACT_MODE}ATTRACT ${ATTRACT_MODE_GENRE}   ${END_IF}${MUSIC_GROUP}\n",
    # navigation sounds, as in Fruitbox's Classic skin (silent while a song plays);
    # every sound also stays silent while Fruitbox is muted (Mute = Left Ctrl)
    "button_press.txt": "${IF_ANY_BUTTON_PRESSED}${IF_NOT_SONG_PLAYING}${IF_NOT_MUTE}${PLAY_SOUND}",
    "record_start.txt": "${IF_SONG_LOADING}${IF_NOT_MUTE}${PLAY_SOUND}",
    # read by cabinet-lights/jukebox-bridge.py (cabinet lights); one condition per line
    "lights_state.txt": (
        "${IF_SONG_PLAYING}PLAYING${ELSE}IDLE\n"
        "${IF_ATTRACT_PLAYING}ATTRACT_SONG${ELSE}USER_SONG\n"
        "${IF_ATTRACT_MODE}ATTRACT_ON${ELSE}ATTRACT_OFF\n"
    ),
    "page_turn.txt": "${IF_TITLE_STRIP_MOVING}${IF_NOT_SONG_PLAYING}${IF_NOT_MUTE}${PLAY_SOUND}",
    "now_playing.txt": (
        "${IF_SONG_PLAYING}${NOW_PLAYING_ARTIST}\n"
        "${IF_SONG_PLAYING}${NOW_PLAYING_ELAPSED_TIME} / ${NOW_PLAYING_LENGTH}${IF_PAUSED}   PAUSED\n"
    ),
    "select_hint.txt": (
        "${IF_INVALID_CHOICE}No such selection${ELSE}${IF_DUPLICATE_CHOICE}Already in the queue"
        "${ELSE}${IF_PLAYQUEUE_FULL}Queue full${ELSE}${IF_FREEPLAY}Enter a 3-digit number"
        "${ELSE}${IF_NO_CREDITS}Insert coin${ELSE}${SONGS_CREDITED} plays credited\n"
    ),
    "coming_up_title.txt": "COMING UP${IF_ANY_COMING_UP}  (${COMING_UP_NUM_SONGS})\n",
    "coming_up.txt": "".join(
        "${IF_SONG_COMING_UP}${COMING_UP_TITLE}  –  ${COMING_UP_ARTIST}\n" for _ in range(4)
    ),
}


def main():
    if not os.path.isdir(FRUITBOX_SKINS):
        sys.exit(f"Fruitbox skins not found at {FRUITBOX_SKINS}; set FRUITBOX_SKINS")
    os.makedirs(OUT, exist_ok=True)
    for f, _ in FONTS:
        shutil.copy(font_file(f), OUT)
    seen = set()
    for g, col in GENRE_COLOURS:
        fn = genre_file(g)
        if fn not in seen:
            make_strip(col, os.path.join(OUT, fn))
            seen.add(fn)
    for wav in (PAGE_TURN_WAV, BUTTON_WAV):
        shutil.copy(os.path.join(FRUITBOX_SKINS, "Classic", wav), OUT)
    shutil.copy(os.path.join(FRUITBOX_SKINS, "Carousel", RECORD_WAV), OUT)
    make_spectrum_bar()
    make_background()
    if LIGHT_BAR_ANIM:
        make_light_bar_frames()
    for name, body in STATUS_FILES.items():
        with open(os.path.join(OUT, name), "w") as fh:
            fh.write(body)
    status_screen.make_files(sys.modules[__name__])
    # status page values (same text as status-page/jukebox_status.txt, plus the skin name)
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "..", "..", "status-page", "jukebox_status.txt")) as src, \
            open(os.path.join(OUT, "jukebox_status.txt"), "w") as fh:
        fh.write("SKIN=" + os.path.basename(os.path.normpath(OUT)) + "\n" + src.read())
    write_cfg()
    print("wrote", OUT)


if __name__ == "__main__":
    main()
