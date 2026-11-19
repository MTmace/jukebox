#!/usr/bin/env bash
# Installs the jukebox state manager (jukebox-state).
#
#   sudo bash /home/mtmace/fruitbox/state-manager/install-state.sh       set it up
#   sudo bash /home/mtmace/fruitbox/state-manager/install-state.sh off   remove it
#
# Needs jukebox-state.py and jukebox-state.service in the same folder as this file.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
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
  systemctl daemon-reload
  echo "State manager removed."
  exit 0
fi

if ! python3 -c "import evdev" 2>/dev/null; then
  apt-get install -y python3-evdev
fi

# virtual keyboard support (to stop the music in Fruitbox on sleep)
modprobe uinput 2>/dev/null || true
echo uinput > /etc/modules-load.d/jukebox-uinput.conf

# no sound to the screens' HDMI: only the DAC (see the comment in the .conf file)
install -d -o mtmace -g mtmace "$WP_DIR"
install -m 644 -o mtmace -g mtmace "$HERE/$WP_RULE" "$WP_DIR/$WP_RULE"
echo "HDMI sound turned off for PipeWire ($WP_DIR/$WP_RULE)."
restart_wireplumber
sleep 3
sinks=$(runuser -u mtmace -- env XDG_RUNTIME_DIR=/run/user/$(id -u mtmace) timeout 5 wpctl status 2>/dev/null \
        | sed -n '/Sinks:/,/Sources:/p' | head -n 8 || true)
echo "$sinks"
if [ -z "$sinks" ]; then      # wpctl didn't answer within 5 s (PipeWire still restarting)
  echo "Sound check skipped (PipeWire didn't answer). Check later with: wpctl status"
elif echo "$sinks" | grep -q HDMI; then
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
