#!/usr/bin/env bash
# Sets up the jukebox status page (http://jukebox.local) and the F24 on-screen status box.
#
#   sudo bash /home/mtmace/fruitbox/status-page/install-status.sh        set it up
#   sudo bash /home/mtmace/fruitbox/status-page/install-status.sh off    remove it
#
# Needs jukebox-status.py, jukebox-status-overlay.py, jukebox-status.service and
# jukebox_status.txt in the same folder as this file.
#
# It also adds one hidden status box to the end of the Fruitbox skin's
# fruitbox.cfg so Fruitbox writes its volume, song and genre to
# /dev/shm/jukebox_fruitbox.txt. The skin file is backed up first
# (fruitbox.cfg.before-status), and nothing else in it is changed.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
SKINS=/opt/fruitbox/skins
STAMP_LINE="Output = /dev/shm/jukebox_fruitbox.txt"

if [ "$(id -u)" != 0 ]; then
  echo "Run it with sudo:  sudo bash $HERE/install-status.sh"
  exit 1
fi

if [ "${1:-}" = off ]; then
  systemctl disable --now jukebox-status 2>/dev/null || true
  rm -f /etc/systemd/system/jukebox-status.service /usr/local/bin/jukebox-status.py /usr/local/bin/jukebox-status-overlay.py
  rm -f /etc/sudoers.d/jukebox-status
  systemctl daemon-reload
  echo "Removed the status page. (The skin's hidden status box is harmless and stays;"
  echo "to undo it too, copy fruitbox.cfg.before-status back over fruitbox.cfg in the skin folder.)"
  exit 0
fi

for f in jukebox-status.py jukebox-status-overlay.py jukebox-status.service jukebox_status.txt; do
  [ -f "$HERE/$f" ] || { echo "Missing $HERE/$f - copy it next to this script first."; exit 1; }
done

python3 -c "import evdev" 2>/dev/null || apt-get install -y python3-evdev
python3 -c "import tkinter" 2>/dev/null || apt-get install -y python3-tk

# 1. Fruitbox skin: hidden status box (only skins that already have the lights' box, i.e. ours)
patched=0
added=0
for cfg in "$SKINS"/*/fruitbox.cfg; do
  [ -f "$cfg" ] || continue
  grep -q "jukebox_state.txt" "$cfg" || continue
  dir="$(dirname "$cfg")"
  name="$(basename "$dir")"
  { echo "SKIN=$name"; tr -d '\r' < "$HERE/jukebox_status.txt"; } > "$dir/jukebox_status.txt"
  if grep -qF "$STAMP_LINE" "$cfg"; then
    echo "Skin \"$name\": status box already there."
  else
    [ -f "$cfg.before-status" ] || cp -p "$cfg" "$cfg.before-status"
    printf '\n# JUKEBOX: hidden status box for the status page (status-page/install-status.sh).\n# Keep it LAST in the file.\n[status]\nPosition = 0 0\nTimerTickPeriod = 1 second\nContents = jukebox_status.txt\n%s\n' "$STAMP_LINE" >> "$cfg"
    echo "Skin \"$name\": status box added (backup: $cfg.before-status)."
    added=1
  fi
  patched=$((patched + 1))
done
[ "$patched" -gt 0 ] || echo "WARNING: no jukebox skin found in $SKINS - volume, song and genre will show '?'."

# 2. Control page: let the page (runs as mtmace) start / stop / restart our own
#    system services, and nothing else. One line per jukebox-*.service installed
#    now; run this installer again after adding a new service.
SUDO_FILE=/etc/sudoers.d/jukebox-status
units=""
for f in /etc/systemd/system/jukebox-*.service; do
  [ -f "$f" ] || continue
  u="$(basename "$f" .service)"
  units="$units $u"
done
units="$units jukebox-status"
{
  echo "# Status page Control page (status-page/install-status.sh). Made by the installer."
  for u in $(echo $units | tr ' ' '\n' | sort -u); do
    echo "mtmace ALL=(root) NOPASSWD: /usr/bin/systemctl start $u, /usr/bin/systemctl stop $u, /usr/bin/systemctl restart $u, /usr/bin/systemctl --no-block restart $u"
  done
} > "$SUDO_FILE.new"
chmod 440 "$SUDO_FILE.new"
if visudo -cf "$SUDO_FILE.new" >/dev/null; then
  mv "$SUDO_FILE.new" "$SUDO_FILE"
  echo "Control page may start / stop / restart:$(echo $units | tr ' ' '\n' | sort -u | tr '\n' ' ')"
else
  rm -f "$SUDO_FILE.new"
  echo "WARNING: couldn't set the control page's permission; its service buttons will say 'failed'."
fi

# 3. The status service
install -m 755 "$HERE/jukebox-status.py" /usr/local/bin/jukebox-status.py
install -m 755 "$HERE/jukebox-status-overlay.py" /usr/local/bin/jukebox-status-overlay.py
install -m 644 "$HERE/jukebox-status.service" /etc/systemd/system/jukebox-status.service
systemctl daemon-reload
systemctl enable jukebox-status
systemctl restart jukebox-status
sleep 3
systemctl --no-pager --lines=5 status jukebox-status || true
echo
if [ "$added" = 1 ]; then
  echo "Done. Reboot once so Fruitbox picks up the skin change:  sudo reboot"
else
  echo "Done. No reboot needed: just refresh the page."
fi
echo "Then open  http://$(hostname | tr 'A-Z' 'a-z').local  (or http://$(hostname -I | awk '{print $1}'))"
echo "on your PC or phone, and press F24 on the macro pad to see it on the main screen."
