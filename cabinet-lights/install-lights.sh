#!/usr/bin/env bash
# Installs the cabinet lights service (jukebox-lights).
#
#   sudo bash /home/mtmace/fruitbox/cabinet-lights/install-lights.sh       set it up
#   sudo bash /home/mtmace/fruitbox/cabinet-lights/install-lights.sh off   remove it
#
# Needs jukebox-lights.py, jukebox-lights.ini and jukebox-lights.service in the
# same folder as this file.
#
# Moving from the old name (jukebox-bridge, up to 1.4): your settings in
# ~/fruitbox/jukebox-bridge.ini become ~/fruitbox/jukebox-lights.ini unchanged,
# the saved on/off, dimmer and theme carry over, and the old service and
# program are removed. Your settings file is never overwritten: the new one in
# this folder is only used when you have none.
#
# Not done here: the LED pin line in /boot/firmware/config.txt (README step 1).
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
FB=/home/mtmace/fruitbox
INI="$FB/jukebox-lights.ini"

if [ "$(id -u)" != 0 ]; then
  echo "Run it with sudo:  sudo bash $HERE/install-lights.sh"
  exit 1
fi

if [ "${1:-}" = off ]; then
  systemctl disable --now jukebox-lights 2>/dev/null || true
  rm -f /etc/systemd/system/jukebox-lights.service /usr/local/bin/jukebox-lights.py
  systemctl daemon-reload
  echo "Removed the cabinet lights service. Your settings ($INI) are kept."
  exit 0
fi

for f in jukebox-lights.py jukebox-lights.ini jukebox-lights.service; do
  [ -f "$HERE/$f" ] || { echo "Missing $HERE/$f - copy it next to this script first."; exit 1; }
done

python3 -c "import serial, evdev" 2>/dev/null || apt-get install -y python3-serial python3-evdev
command -v parec >/dev/null || apt-get install -y pulseaudio-utils

# 1. The old jukebox-bridge: stop it first so the two never drive the strips at once.
if [ -f /etc/systemd/system/jukebox-bridge.service ]; then
  systemctl disable --now jukebox-bridge 2>/dev/null || true
  rm -f /etc/systemd/system/jukebox-bridge.service
  echo "Old jukebox-bridge service stopped and removed."
fi
rm -f /usr/local/bin/jukebox-bridge.py

# 2. Settings: keep yours.
if [ ! -f "$INI" ] && [ -f "$FB/jukebox-bridge.ini" ]; then
  mv "$FB/jukebox-bridge.ini" "$INI"
  echo "Your settings moved: jukebox-bridge.ini -> jukebox-lights.ini (unchanged)."
elif [ ! -f "$INI" ]; then
  install -o mtmace -g mtmace -m 644 "$HERE/jukebox-lights.ini" "$INI"
  echo "Settings installed: $INI"
else
  echo "Keeping your settings: $INI"
fi
if [ -f "$FB/jukebox-bridge.ini" ]; then
  mv "$FB/jukebox-bridge.ini" "$FB/jukebox-bridge.ini.old"
  echo "(An old jukebox-bridge.ini was left over; renamed to jukebox-bridge.ini.old.)"
fi

# 3. Saved on/off, dimmer and theme.
if [ -d /var/lib/jukebox-bridge ]; then
  mkdir -p /var/lib/jukebox-lights
  [ -f /var/lib/jukebox-lights/lights.json ] || cp -p /var/lib/jukebox-bridge/lights.json /var/lib/jukebox-lights/ 2>/dev/null || true
  rm -rf /var/lib/jukebox-bridge
fi

# 4. Program and service.
install -m 755 "$HERE/jukebox-lights.py" /usr/local/bin/jukebox-lights.py
install -m 644 "$HERE/jukebox-lights.service" /etc/systemd/system/jukebox-lights.service
systemctl daemon-reload
systemctl enable jukebox-lights >/dev/null 2>&1
systemctl restart jukebox-lights
sleep 2
if systemctl is-active --quiet jukebox-lights; then
  echo "jukebox-lights $(grep -m1 '^VERSION' /usr/local/bin/jukebox-lights.py | cut -d'"' -f2) is running."
else
  echo "jukebox-lights did not start. See: journalctl -u jukebox-lights -n 30"
  exit 1
fi
echo "If the status page is installed, run its installer again so its Control page knows the new name:"
echo "  sudo bash $FB/status-page/install-status.sh"
