#!/usr/bin/env bash
# Installs the jukebox state manager (jukebox-state) and retires the old
# macro pad key service (jukebox-keys), which it replaces. Only one of them
# may run, or they would fight over the screens. It also retires the older
# sleep pieces (nightly screen-sleep.sh cron job, xbindkeys Pause binding),
# keeping copies in ~/fruitbox/backup-before-state-manager/retired.
#
#   sudo bash /home/mtmace/fruitbox/state-manager/install-state.sh       set it up
#   sudo bash /home/mtmace/fruitbox/state-manager/install-state.sh off   go back to jukebox-keys
#
# Needs jukebox-state.py and jukebox-state.service in the same folder as this file.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
BACKUP=/home/mtmace/fruitbox/backup-before-state-manager
WP_DIR=/home/mtmace/.config/wireplumber/wireplumber.conf.d
WP_RULE=51-jukebox-no-hdmi-audio.conf

# restart mtmace's WirePlumber so a sound rule change takes effect (no reboot)
restart_wireplumber() {
  runuser -u mtmace -- env XDG_RUNTIME_DIR=/run/user/$(id -u mtmace) \
    systemctl --user restart wireplumber && echo "WirePlumber restarted (sound re-routed)." \
    || echo "Could not restart WirePlumber; the sound rule takes effect after a reboot."
}

if [ "$(id -u)" != 0 ]; then
  echo "Run it with sudo:  sudo bash $HERE/install-state.sh"
  exit 1
fi

if [ "${1:-}" = off ]; then
  systemctl disable --now jukebox-state 2>/dev/null || true
  pkill -CONT -x fruitbox 2>/dev/null || true     # never leave Fruitbox paused
  rm -f /etc/systemd/system/jukebox-state.service /usr/local/bin/jukebox-state.py /dev/shm/jukebox_mode
  if [ -f "$WP_DIR/$WP_RULE" ]; then
    rm -f "$WP_DIR/$WP_RULE"
    echo "HDMI sound rule removed."
    restart_wireplumber
  fi
  if [ -f "$BACKUP/jukebox-keys.py" ] && [ -f "$BACKUP/jukebox-keys.service" ]; then
    install -m 755 "$BACKUP/jukebox-keys.py" /usr/local/bin/jukebox-keys.py
    install -m 644 "$BACKUP/jukebox-keys.service" /etc/systemd/system/jukebox-keys.service
    systemctl daemon-reload
    systemctl enable --now jukebox-keys
    echo "State manager removed; the old jukebox-keys service is back."
  else
    systemctl daemon-reload
    echo "State manager removed. No jukebox-keys backup found to put back."
  fi
  exit 0
fi

if ! python3 -c "import evdev" 2>/dev/null; then
  apt-get install -y python3-evdev
fi

# virtual keyboard support (to stop the music in Fruitbox on sleep)
modprobe uinput 2>/dev/null || true
echo uinput > /etc/modules-load.d/jukebox-uinput.conf

# retire jukebox-keys, keeping a copy so "off" can put it back
if [ -f /usr/local/bin/jukebox-keys.py ] || [ -f /etc/systemd/system/jukebox-keys.service ]; then
  mkdir -p "$BACKUP"
  cp -p /usr/local/bin/jukebox-keys.py "$BACKUP/" 2>/dev/null || true
  cp -p /etc/systemd/system/jukebox-keys.service "$BACKUP/" 2>/dev/null || true
  chown -R mtmace:mtmace "$BACKUP"
  systemctl disable --now jukebox-keys 2>/dev/null || true
  rm -f /etc/systemd/system/jukebox-keys.service /usr/local/bin/jukebox-keys.py
  echo "Old jukebox-keys service stopped and removed (copy in $BACKUP)."
fi

# retire the older sleep pieces that decided sleep on their own (the state
# manager is now the only one): the nightly screen-sleep.sh cron job, the
# xbindkeys Pause binding, and the old scripts. Copies go to $BACKUP.
mkdir -p "$BACKUP/retired"
for who in mtmace root; do
  if crontab -u "$who" -l 2>/dev/null | grep -q 'screen-sleep'; then
    crontab -u "$who" -l > "$BACKUP/retired/crontab-$who"
    { grep -v 'screen-sleep' "$BACKUP/retired/crontab-$who" || true; } | crontab -u "$who" -
    echo "Removed the screen-sleep.sh cron job for $who (old crontab in $BACKUP/retired)."
  fi
done
XBK=/home/mtmace/.xbindkeysrc
if [ -f "$XBK" ] && grep -q 'screen-sleep' "$XBK"; then
  cp -p "$XBK" "$BACKUP/retired/xbindkeysrc"
  # each binding is a "command" line then a key line: drop both for screen-sleep
  awk '/screen-sleep/ {skip=1; next} skip {skip=0; next} {print}' "$BACKUP/retired/xbindkeysrc" > "$XBK"
  chown mtmace:mtmace "$XBK"
  if pgrep -x xbindkeys >/dev/null; then
    pkill -x xbindkeys || true
    if grep -qv '^[[:space:]]*\(#.*\)\?$' "$XBK"; then     # other bindings left: start it again
      runuser -u mtmace -- env DISPLAY=:0 XAUTHORITY=/home/mtmace/.Xauthority xbindkeys || true
    fi
  fi
  echo "Removed the xbindkeys Pause -> screen-sleep.sh binding (old file in $BACKUP/retired)."
fi
for f in screen-sleep.sh install-screen-sleep.sh install-sleep-key.sh jukebox-keys.py \
         jukebox-keys.service install-keys.sh; do
  if [ -f "/home/mtmace/fruitbox/$f" ]; then
    mv "/home/mtmace/fruitbox/$f" "$BACKUP/retired/"
    echo "Moved the old ~/fruitbox/$f to $BACKUP/retired."
  fi
done
rm -f /dev/shm/jukebox_sleep          # the old sleep flag; nothing reads it now
chown -R mtmace:mtmace "$BACKUP"

# no sound to the screens' HDMI: only the DAC (see the comment in the .conf file)
install -d -o mtmace -g mtmace "$WP_DIR"
install -m 644 -o mtmace -g mtmace "$HERE/$WP_RULE" "$WP_DIR/$WP_RULE"
echo "HDMI sound turned off for PipeWire ($WP_DIR/$WP_RULE)."
restart_wireplumber
sleep 3
sinks=$(runuser -u mtmace -- env XDG_RUNTIME_DIR=/run/user/$(id -u mtmace) wpctl status 2>/dev/null \
        | sed -n '/Sinks:/,/Sources:/p' | head -n 8)
echo "$sinks"
if echo "$sinks" | grep -q HDMI; then
  echo "WARNING: HDMI sound outputs are still there - the rule did not take. Tell Claude."
else
  echo "Sound check: no HDMI sound outputs left, only the DAC."
fi

install -m 755 "$HERE/jukebox-state.py" /usr/local/bin/jukebox-state.py
install -m 644 "$HERE/jukebox-state.service" /etc/systemd/system/jukebox-state.service
systemctl daemon-reload
systemctl enable jukebox-state
systemctl restart jukebox-state
pkill -CONT -x fruitbox 2>/dev/null || true       # in case it was asleep (paused) before
sleep 3
systemctl --no-pager --lines=8 status jukebox-state || true
echo
echo "Done. The state is in /dev/shm/jukebox_mode:  cat /dev/shm/jukebox_mode"
echo "Watch it:  tail -f /home/mtmace/fruitbox/jukebox-state.log"
echo "Sleep = Pause twice. Reboot F20, Rebuild F21, Shut Down F22: each twice within 5 s."
echo "Sound check after each sleep/wake is in the same log (look for 'sound after')."
