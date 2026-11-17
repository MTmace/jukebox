#!/usr/bin/env bash
# One-time setup on the Pi (Raspberry Pi OS desktop, Bookworm or later):
#   - boots straight to the desktop logged in as you
#   - stops the screen blanking
#   - starts Fruitbox fullscreen at login via ~/.config/autostart
#   - keeps the Windows music share awake (no slow first pick after idle)
# Run as your normal user (not with sudo):   bash install-autostart.sh
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
FB_HOME="$HOME/fruitbox"
mkdir -p "$FB_HOME" "$HOME/.config/autostart"

install -m 755 "$HERE/launch-fruitbox.sh" "$FB_HOME/launch-fruitbox.sh"
install -m 755 "$HERE/genre_library.py"   "$FB_HOME/genre_library.py"
install -m 755 "$HERE/send-song-codes.py" "$FB_HOME/send-song-codes.py"
[ -f "$FB_HOME/genre_map.txt" ] || install -m 644 "$HERE/genre_map.txt" "$FB_HOME/genre_map.txt"
if [ -f "$FB_HOME/fruitbox.ini" ]; then
  echo "keeping existing $FB_HOME/fruitbox.ini"
else
  install -m 644 "$HERE/fruitbox.ini" "$FB_HOME/fruitbox.ini"
fi

cat > "$HOME/.config/autostart/fruitbox.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Fruitbox Jukebox
Exec=bash $FB_HOME/launch-fruitbox.sh
X-GNOME-Autostart-enabled=true
EOF

# Every 4 minutes, list the music share so Windows doesn't drop the idle
# connection; otherwise the first pick after a quiet spell waits seconds.
KEEPALIVE="*/4 * * * * ls /mnt/music >/dev/null 2>&1"
( crontab -l 2>/dev/null | grep -vF "ls /mnt/music" || true
  echo "$KEEPALIVE"
) | crontab -

sudo raspi-config nonint do_boot_behaviour B4   # desktop, auto-login
sudo raspi-config nonint do_blanking 1          # never blank the screen
sudo apt-get install -y python3-mutagen         # for genre_library.py

echo "Done. Next: python3 $FB_HOME/genre_library.py --ini $FB_HOME/fruitbox.ini"
echo "Then reboot. To stop autostart: rm ~/.config/autostart/fruitbox.desktop"
