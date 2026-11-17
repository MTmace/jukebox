"""Second (status) display for the Firestar skin: Fruitbox display 2.

build_skin.py imports this and calls the three hooks below, so the status
screen is regenerated with the rest of the skin.

Laid out for the Celesttouch 14.5" 2560x720 (32:9) bar panel behind clear
glass in the right-hand panel beside the keypad (opening 14.75 x 4.74", the
picture is about 13.96 x 3.93", so all of it shows). One row: coming up,
now playing with cover art and a 7-segment clock, then the selection readout
over a spectrum well, then a vertical volume meter (Andrew 2026-10-16).
No touch (it sits behind glass).

Only the light-bar ribbon on top, no header (Andrew 2026-10-15). The bar
and the main screen both list the queue from the next song (see the note on
status_coming_up.txt).
Reuses the main skin's fonts (fonts are numbered once for the whole cfg), its
select_hint.txt, select_ghost.txt, art_blank.png, spectrum bar and colours.
"""
import os

from PIL import Image, ImageDraw, ImageFilter

W, H = 2560, 720                   # status screen skin size (32:9 bar panel)
DISPLAY = 2
RIBBON_H = 16                      # light-bar ribbon along the top (no header: Andrew 2026-10-15)
ROW_Y, ROW_B = RIBBON_H + 18, H - 20   # top / bottom of the panel row
GAP = 24
NP_W, CU_W = 1110, 720             # now playing / coming up widths; selection gets the rest
VOL_PW = 180                       # volume panel at the far right (Andrew 2026-10-16)
ART = 560                          # cover art size
COMING_UP_LINES = 14                # fills the list box (40 px per line, Andrew wants more)
ART_BLANK = "art_blank.png"        # main screen's idle cover, baked in behind the art box
SPEC_BARS = 8
LED_FONT = 12                      # main screen's 7-segment readout font (technology-mono 152)
LED_TOP, LED_H = 7, 84             # digits start 7 px into a font-12 box and are 84 px tall
LED_BOX_H = 124                    # readout panel height; digits sit centred in it
CLOCK_W = 400
VOL_W, VOL_SEGS = 72, 20          # vertical volume LED bar, fills upward; 20 = one segment per
                                   # SongVolumeStep of 5, so the bar always shows whole segments
RIBBON_DIR = "lightbars2"          # twinkle frames for the ribbon, like the main screen's lightbars/


def boxes():
    x0 = 24
    cu = (x0, ROW_Y, x0 + CU_W, ROW_B)                       # coming up on the left,
    np_ = (cu[2] + GAP, ROW_Y, cu[2] + GAP + NP_W, ROW_B)    # now playing in the centre (Andrew 2026-10-24)
    sel = (np_[2] + GAP, ROW_Y, W - 24 - VOL_PW - GAP, ROW_B)
    return np_, cu, sel


def vol_panel():
    return W - 24 - VOL_PW, ROW_Y, W - 24, ROW_B


def art_box():
    np_ = boxes()[0]
    return np_[0] + 30, np_[1] + (np_[3] - np_[1] - ART) // 2, ART


def text_x():
    ax, _, aw = art_box()
    return ax + aw + 34


def clock_box():
    np_ = boxes()[0]
    cx = (text_x() + np_[2] - 30) // 2          # centred in the text column
    y = np_[3] - 24 - 62 - LED_BOX_H             # at the bottom of the panel, track length just under it (Andrew 2026-10-16)
    return cx - CLOCK_W // 2, y, cx + CLOCK_W // 2, y + LED_BOX_H


def code_box():
    sel = boxes()[2]
    return sel[0] + 30, sel[1] + 76, sel[2] - 30, sel[1] + 76 + LED_BOX_H


def vol_box():
    """Vertical volume LED bar in its own panel, under the heading and readout."""
    p = vol_panel()
    cx = (p[0] + p[2]) // 2
    return cx - VOL_W // 2, p[1] + 150, cx + VOL_W // 2, p[3] - 28


def vol_segments(lit):
    """Segmented LED bar image, lime at the bottom to red at the top, lit or ghosted."""
    vh = vol_box()[3] - vol_box()[1]
    im = Image.new("RGBA", (VOL_W, vh), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    seg = vh / VOL_SEGS
    for i in range(VOL_SEGS):           # i = 0 is the bottom segment
        t = i / (VOL_SEGS - 1)
        if t < 0.6:
            c = (176, 230, 40)
        elif t < 0.85:
            c = (255, 210, 20)
        else:
            c = (255, 58, 48)
        if not lit:
            c = tuple(v // 5 for v in c)
        y1 = vh - round(i * seg) - 2
        d.rounded_rectangle((2, round(vh - (i + 1) * seg) + 3, VOL_W - 3, y1), 3, fill=c + (255,))
    return im


def led_y(box):
    """Status box y that centres font-12 digits in a readout panel."""
    return box[1] + (box[3] - box[1] - LED_H) // 2 - LED_TOP


def spectrum_box():
    sel = boxes()[2]
    return sel[0] + 30, sel[1] + 280, sel[2] - 30, sel[3] - 24


def make_background(bs):
    im = bs.vgrad(W, H, (30, 8, 6), (8, 6, 10))
    d = ImageDraw.Draw(im)
    np_, cu, sel = boxes()

    # just the red/orange/yellow light-bar ribbon along the top
    d.rectangle((0, 0, W, RIBBON_H), fill=(6, 4, 6))
    bs.light_bars(im, (0, 1, W, RIBBON_H - 2))

    bs.rounded_panel(im, np_, glow=bs.FIRE)
    bs.rounded_panel(im, cu, glow=bs.FIRE)
    bs.rounded_panel(im, sel, glow=bs.AMBER)
    vp = vol_panel()
    bs.rounded_panel(im, vp, glow=bs.FIRE)

    ax, ay, aw = art_box()
    d.rectangle((ax - 6, ay - 6, ax + aw + 5, ay + aw + 5), fill=(40, 40, 46), outline=bs.CHROME_HI, width=3)
    # idle cover, same image as the main screen; the art box skips drawing
    # (${NO_DRAW}) when nothing plays, so this shows through. Not a status
    # Bitmap: those abort Fruitbox when display 2 is missing.
    blank = os.path.join(bs.OUT, ART_BLANK)
    if os.path.exists(blank):
        im.paste(Image.open(blank).convert("RGB").resize((aw, aw), Image.LANCZOS), (ax, ay))

    hf = bs.font(4)
    d.text((text_x(), np_[1] + 14), "NOW PLAYING", font=hf, fill=bs.FIRE)
    tw = d.textlength("SELECTION", font=hf)       # red heading, as on the main screen
    d.text(((sel[0] + sel[2] - tw) / 2, sel[1] + 12), "SELECTION", font=hf, fill=bs.FIRE)
    tw = d.textlength("VOLUME", font=hf)
    d.text(((vp[0] + vp[2] - tw) / 2, vp[1] + 12), "VOLUME", font=hf, fill=bs.FIRE)

    vx0, vy0, vx1, vy1 = vol_box()                # unlit volume segments; the lit bar is clipped over them
    im.paste(vol_segments(False), (vx0, vy0), vol_segments(False))
    vol_segments(True).save(os.path.join(bs.OUT, "vol_bar.png"))

    for box in (clock_box(), code_box()):         # selection box copies the clock's border (Andrew)
        d.rounded_rectangle(box, 12, fill=(10, 4, 4), outline=(90, 40, 20), width=3)
    d.rounded_rectangle(spectrum_box(), 12, fill=(6, 6, 8), outline=(60, 60, 70), width=2)

    im.save(os.path.join(bs.OUT, "status_background.png"), optimize=True)


STATUS_FILES = {
    "status_details.txt": (
        "${IF_SONG_PLAYING}${NOW_PLAYING_ARTIST}\n"
        "${IF_SONG_PLAYING}${NOW_PLAYING_ALBUM}\n"
        "${IF_SONG_PLAYING}${NOW_PLAYING_YEAR}\n"          # own line (Andrew 2026-10-16)
        "\n"                                               # blank line, then the length (Andrew 2026-10-24)
        "${IF_SONG_PLAYING}Track length: ${NOW_PLAYING_LENGTH}\n"
        "${IF_SONG_PLAYING}${NOW_PLAYING_PUBLISHER}\n"   # format and bit rate, written by strip_titles.py (Andrew 2026-10-26)
    ),
    "status_time.txt": "${IF_SONG_PLAYING}${NOW_PLAYING_ELAPSED_TIME}\n",
    "status_time_ghost.txt": "${IF_FREEPLAY}88:88${ELSE}88:88\n",  # needs a ${...} or Fruitbox draws a black box
    "status_length.txt": "${IF_PAUSED}PAUSED\n",      # under the clock; the length is in the track info
    # Each ${COMING_UP_*} field (and ${IF_SONG_COMING_UP}) keeps its own place
    # in the queue, read in cfg order. The main screen uses TITLE, ARTIST and
    # IF_SONG_COMING_UP, so this list uses CUSTOM_TAG (short title) and ISRC
    # ("–  artist", written there by strip_titles.py) and starts at the next song
    # too. No IF guard here: past the end of the queue the fields are blank.
    # one line per song, "Title  –  Artist" like the main screen; the dash is
    # part of the ISRC field so rows past the end of the queue stay blank
    "status_coming_up.txt": "${COMING_UP_CUSTOM_TAG}  ${COMING_UP_ISRC}\n" * COMING_UP_LINES,
    "status_coming_up_title.txt": "COMING UP${IF_ANY_COMING_UP}  (${COMING_UP_NUM_SONGS})\n",
}


def make_ribbon_frames(bs):
    """Twinkle frames for the ribbon, made the same way as the main screen's
    light bars (bs.make_light_bar_frames), at this screen's width."""
    import math
    import random
    d = os.path.join(bs.OUT, RIBBON_DIR)
    os.makedirs(d, exist_ok=True)
    for old in os.listdir(d):
        os.remove(os.path.join(d, old))
    n = bs.LIGHT_BAR_FRAMES
    rnd = random.Random(1960)
    plan = [(rnd.choice((1, 1, 1, 2)), rnd.random()) for _ in range(W // bs.LIGHT_BAR_PITCH + 3)]
    for f in range(n):
        t = f / n
        def level(i, t=t):
            times, phase = plan[i]
            p = (t * times + phase) % 1.0
            flare = math.cos((p - 0.5) * math.pi * 12) if abs(p - 0.5) < 1 / 24 else 0.0
            return 0.88 + 0.5 * flare
        im = Image.new("RGB", (W, RIBBON_H), (6, 4, 6))
        bs.light_bars(im, (0, 1, W, RIBBON_H - 2), level=level)
        im.save(os.path.join(d, f"bars_{f:02d}.png"), optimize=True)


def make_files(bs):
    """Images and status text files for display 2 (called from build_skin.main)."""
    make_background(bs)
    if bs.LIGHT_BAR_ANIM:
        make_ribbon_frames(bs)
    for name, body in STATUS_FILES.items():
        with open(os.path.join(bs.OUT, name), "w") as fh:
            fh.write(body)


def general_lines():
    """Lines for [general] (called from build_skin.write_cfg)."""
    return [f"SkinSize = {DISPLAY} {W} {H}"]


def cfg_lines(bs):
    """Display 2 objects, appended at the end of fruitbox.cfg."""
    text = bs.text
    np_, cu, sel = boxes()
    ax, ay, aw = art_box()
    tx = text_x()
    tw = np_[2] - 30 - tx
    L = []

    def obj(kind, x, y, w, h, *extra):
        L.append(f"[{kind}]")
        L.append(f"DisplayNumber = {DISPLAY}")
        L.append(f"Position = {x} {y}")
        L.append(f"Size = {w} {h}")
        L.extend(extra)
        L.append("")

    L.append("# Status screen (display 2, 2560x720 bar panel), generated from status_screen.py.")
    L.append("# Fruitbox skips these if only one monitor is connected.")
    L.append("")
    obj("bitmap", 0, 0, W, H, "File = status_background.png")
    if bs.LIGHT_BAR_ANIM:
        # twinkling ribbon, like the main screen's light bars. A Bitmap on a
        # display-2 [status] stops Fruitbox if the bar screen isn't detected.
        L.append("# ---- twinkling light-bar ribbon (frames in lightbars2/) ----")
        obj("status", 0, 0, W, RIBBON_H,
            f"TimerTickPeriod = {bs.LIGHT_BAR_TICKS}",
            *[f"Bitmap = {RIBBON_DIR}/bars_{f:02d}.png" for f in range(bs.LIGHT_BAR_FRAMES)],
            'Initial = "${DRAW_BITMAP}"',
            'Contents = "${IF_TIMER_TICK}${DRAW_BITMAP}"')

    L.append("# ---- now playing ----")
    obj("status", ax, ay, aw, aw, "Contents = \"${IF_SONG_PLAYING}${NOW_PLAYING_ARTWORK}${ELSE}${NO_DRAW}\"")
    obj("status", tx, np_[1] + 80, tw, 60,
        "Text = " + text(5, (255, 244, 225), align="left", mode=bs.TITLE_SCROLL, maxw=tw),
        bs.TITLE_TICK,
        "Contents = \"${IF_SONG_PLAYING}${NOW_PLAYING_TITLE}${ELSE}Make your selection\"")
    obj("status", tx, np_[1] + 150, tw, 300,
        "Text = " + text(6, (210, 200, 190), align="left", maxw=tw),
        "LineSpacing = 10",
        "Contents = status_details.txt")
    cx0, cy0, cx1, cy1 = clock_box()
    for contents, colour in (("status_time_ghost.txt", bs.LED_GHOST), ("status_time.txt", bs.LED_ON)):
        obj("status", cx0, led_y(clock_box()), cx1 - cx0, LED_TOP + LED_H + 10,
            "Text = " + text(LED_FONT, colour), f"Contents = {contents}")
    # PAUSED under the clock, in the main screen's grey
    obj("status", cx0 - 60, cy1 + 14, cx1 - cx0 + 120, 48,
        "Text = " + text(6, (210, 200, 190)),
        "Contents = status_length.txt")

    L.append("# ---- volume panel: readout over a vertical LED bar that fills upward with ${VOLUME} ----")
    vp = vol_panel()
    vx0, vy0, vx1, vy1 = vol_box()
    vh = vy1 - vy0
    obj("status", vp[0] + 10, vp[1] + 74, vp[2] - vp[0] - 20, 56,
        "Text = " + text(4, (255, 244, 225)),
        "Contents = \"${IF_MUTE}MUTED${ELSE}${VOLUME}\"")
    # Clip is in screen pixels: its top moves up from the bar's bottom as its height grows
    obj("bitmap", vx0, vy0, VOL_W, vh,
        "File = vol_bar.png", f"Clip = {vx0} {vy1 - 1} [{vy0} ${{VOLUME}}] {VOL_W} 1 [{vh} ${{VOLUME}}]")

    L.append("# ---- coming up ----")
    cw = cu[2] - cu[0] - 56
    obj("status", cu[0] + 28, cu[1] + 16, cw, 56,
        "Text = " + text(4, bs.FIRE, align="left"),
        "Contents = status_coming_up_title.txt")
    obj("status", cu[0] + 28, cu[1] + 80, cw, cu[3] - cu[1] - 96,
        "Text = " + text(6, (210, 200, 190), align="left", maxw=cw),
        "LineSpacing = 6",
        "Contents = status_coming_up.txt")

    L.append("# ---- selection readout ----")
    sx0, sy0, sx1, sy1 = code_box()
    for contents, colour in (("select_ghost.txt", bs.LED_GHOST), ("\"${SELECT_CODE}\"", bs.LED_ON)):
        obj("status", sx0, led_y(code_box()), sx1 - sx0, LED_TOP + LED_H + 10,
            "Text = " + text(LED_FONT, colour), f"Contents = {contents}")
    obj("status", sel[0] + 10, sy1 + 8, sel[2] - sel[0] - 20, 44,
        "Text = " + text(6, (210, 200, 190)),
        "Contents = select_hint.txt")

    L.append("# ---- spectrum under the selection readout (live, from the music) ----")
    px0, py0, px1, py1 = spectrum_box()
    half = (px1 - px0 - 48) // 2
    for x, flip, chan, bands in ((px0 + 16, "yes", "left", (0, 2, 4, 6, 9, 12, 15, 18)),
                                 (px0 + 32 + half, "no", "right", (1, 3, 5, 7, 10, 13, 16, 19))):
        obj("spectrum", x, py0 + 14, half, py1 - py0 - 28,
            "Bitmap = spectrum.png", "Mode = scaled", f"HorizontalFlip = {flip}",
            f"Channel = {chan}", "Decay = 3", *[f"Band = {b} 1.0 0 0" for b in bands[:SPEC_BARS]])
    return L
