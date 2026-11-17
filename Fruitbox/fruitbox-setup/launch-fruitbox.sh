#!/usr/bin/env bash
# Starts Fruitbox v3 with the jukebox's own ini, and restarts it if it crashes.
# Installed to ~/fruitbox/ by install-autostart.sh and run at desktop login.
#
# Quitting from the keyboard (Esc / Quit button) exits cleanly and is NOT
# restarted, so you can get to the desktop for maintenance. A crash is
# restarted after 3 seconds, up to 5 times in a row.

FB_HOME="$HOME/fruitbox"
INI="$FB_HOME/fruitbox.ini"
LOG="$FB_HOME/fruitbox.log"
SKIN="/opt/fruitbox/skins/Firestar Ultrawide/fruitbox.cfg"   # "" = show the skin chooser instead
WAIT_FOR="$HOME/JukeboxGenres" # folder that must exist first (USB music drive mount)

APP_DIR="/opt/fruitbox"
export GST_PLUGIN_PATH="$APP_DIR/lib/gstreamer-1.0${GST_PLUGIN_PATH:+:$GST_PLUGIN_PATH}"
export GST_PLUGIN_SCANNER="$APP_DIR/libexec/gstreamer-1.0/gst-plugin-scanner"
export LD_LIBRARY_PATH="$APP_DIR/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

for _ in $(seq 30); do [ -d "$WAIT_FOR" ] && break; sleep 1; done

# Fruitbox stops with "Can't find path" if any MusicPath folder is missing
# (e.g. a genre that lost its last song). Drop those lines from the ini first.
python3 - "$INI" "$HOME/JukeboxLibrary" <<'PY' >> "$FB_HOME/launcher.log" 2>&1
import os, re, sys, time
ini, fallback = sys.argv[1], sys.argv[2]
try:
    lines = open(ini, encoding="utf-8").read().splitlines()
except OSError:
    sys.exit(0)
keep, dropped, paths = [], [], 0
for ln in lines:
    m = re.match(r"\s*MusicPath\s*=\s*([^=]*?)\s*(=.*)?$", ln, re.I)
    if m:
        p = os.path.expanduser(os.path.expandvars(m.group(1)))
        if not os.path.isdir(p):
            dropped.append(m.group(1))
            continue
        paths += 1
    keep.append(ln)
if not dropped:
    sys.exit(0)
if paths == 0:                       # nothing left: play the whole library
    i = next((n + 1 for n, ln in enumerate(keep) if ln.strip().lower() == "[general]"), 0)
    keep.insert(i, f"  MusicPath = {fallback}")
stamp = time.strftime("%F %T")
for p in dropped:
    print(f"{stamp} removed missing MusicPath {p} from {ini}")
with open(ini + ".tmp", "w", encoding="utf-8") as fh:
    fh.write("\n".join(keep) + "\n")
os.replace(ini + ".tmp", ini)
PY

# Keep the Windows music share awake: every 4 minutes cron lists it so the
# first pick after a quiet spell isn't delayed. Add the job if it's missing.
KEEPALIVE="*/4 * * * * ls /mnt/music >/dev/null 2>&1"
if ! crontab -l 2>/dev/null | grep -qF "$KEEPALIVE"; then
  ( crontab -l 2>/dev/null | grep -vF "ls /mnt/music" || true
    echo "$KEEPALIVE"
  ) | crontab - &&
    echo "$(date '+%F %T') added music share keep-alive to crontab" >> "$FB_HOME/launcher.log"
fi

# Set both monitors' resolutions before Fruitbox starts. Under X11 the Pi
# sometimes boots both outputs mirrored at 1024x768, which stretches the skin.
# Ultrawide on HDMI-1 at the left, bar panel on HDMI-2 to its right.
# The ultrawide is mounted upside down, so its picture is turned 180 degrees
# (MAIN_ROTATE=normal turns that off). The bar panel is never rotated.
MAIN_ROTATE=inverted
screens_right() {   # both screens already at the right size and place?
  local q; q=$(xrandr 2>/dev/null)
  grep -q "^HDMI-1 connected primary 3440x1440+0+0 $( [ "$MAIN_ROTATE" = normal ] && echo '(' || echo "$MAIN_ROTATE" )" <<<"$q" &&
    grep -q '^HDMI-2 connected 2560x720+3440+0' <<<"$q"
}
# Only touch the screens when they're wrong: changing them just before
# Fruitbox opens its windows can leave Fruitbox not full screen.
if command -v xrandr >/dev/null 2>&1 && ! screens_right; then
  # The bar panel doesn't always report 2560x720 at boot, so add the mode by hand.
  xrandr --newmode 2560x720 119.0 2560 2608 2640 2720 720 723 728 730 +hsync -vsync >/dev/null 2>&1
  xrandr --addmode HDMI-2 2560x720 >/dev/null 2>&1
  screens_ok=no
  for _ in $(seq 10); do
    xrandr --output HDMI-1 --mode 3440x1440 --rotate "$MAIN_ROTATE" --pos 0x0 --primary \
           --output HDMI-2 --mode 2560x720 --pos 3440x0 >/dev/null 2>&1 && { screens_ok=yes; break; }
    sleep 1
  done
  # Fallback: never leave the bar overlapping the ultrawide at 0x0.
  [ "$screens_ok" = yes ] || xrandr --output HDMI-1 --mode 3440x1440 --rotate "$MAIN_ROTATE" --pos 0x0 --primary --output HDMI-2 --auto --pos 3440x0 >/dev/null 2>&1 \
    || xrandr --output HDMI-1 --mode 3440x1440 --rotate "$MAIN_ROTATE" --pos 0x0 --primary >/dev/null 2>&1   # bar unplugged
  sleep 3   # let the desktop finish resizing before Fruitbox opens
  echo "$(date '+%F %T') screens: $(xrandr 2>/dev/null | grep ' connected' | cut -d'(' -f1 | tr '\n' ' ')" >> "$FB_HOME/launcher.log"
fi

# Pi (desktop) volume at 100% and unmuted, so the Fruitbox volume (= / - keys,
# shown on the second screen) is the only volume control; the amp sets the max.
if command -v wpctl >/dev/null 2>&1; then
  wpctl set-volume @DEFAULT_AUDIO_SINK@ 1.0 >/dev/null 2>&1
  wpctl set-mute @DEFAULT_AUDIO_SINK@ 0 >/dev/null 2>&1
fi

args=(--ini "$INI" --log "$LOG")
[ -n "$SKIN" ] && args+=(--skin "$SKIN")

# Tell the keypad Teensy which selection codes this skin has, so it never
# sends digits Fruitbox would ignore (send-song-codes.py, logged to launcher.log).
python3 "$FB_HOME/send-song-codes.py" "${SKIN:-/opt/fruitbox/skins/Firestar Ultrawide/fruitbox.cfg}"

cd "$APP_DIR" || exit 1
fails=0
while :; do
  "$APP_DIR/fruitbox" "${args[@]}"
  code=$?
  [ "$code" -eq 0 ] && exit 0
  fails=$((fails + 1))
  echo "$(date '+%F %T') fruitbox exited with $code (restart $fails)" >> "$FB_HOME/launcher.log"
  [ "$fails" -ge 5 ] && exit "$code"
  sleep 3
done
