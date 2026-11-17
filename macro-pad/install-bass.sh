#!/bin/bash
# Installs the jukebox bass knob. Run as mtmace (NOT with sudo):
#   bash /home/mtmace/fruitbox/install-bass.sh
# Expects jukebox-bass.py, jukebox-bass.conf and jukebox-bass.service in
# /home/mtmace/fruitbox/. It will ask for your password once (apt install).
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
if [ "$(id -u)" = 0 ]; then
  echo "Run this WITHOUT sudo:  bash $DIR/install-bass.sh"; exit 1
fi
for f in jukebox-bass.py jukebox-bass.conf jukebox-bass.service; do
  [ -f "$DIR/$f" ] || { echo "Missing $DIR/$f"; exit 1; }
done
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"

echo "== 1. Tools"
sudo apt-get install -y python3-evdev pipewire-bin pulseaudio-utils

if grep -qs equal /etc/asound.conf; then
  echo
  echo "!! /etc/asound.conf mentions 'equal' (the alsaequal setup). That sends"
  echo "!! sound straight to the DAC around PipeWire and fights this bass knob"
  echo "!! (and the sound-reactive cabinet lights). Moving it aside:"
  sudo mv /etc/asound.conf /etc/asound.conf.alsaequal-off
  echo "!! now /etc/asound.conf.alsaequal-off"
fi

echo "== 2. Find the DAC"
CONF="$HOME/.config/pipewire/pipewire.conf.d/jukebox-bass.conf"
DAC="$(pactl get-default-sink 2>/dev/null || true)"
if [ "$DAC" = "jukebox_bass" ] || [ -z "$DAC" ]; then
  # already installed once: keep the DAC name we found last time
  DAC="$(grep -o 'target.object = "[^"]*"' "$CONF" 2>/dev/null | cut -d'"' -f2)"
fi
if [ -z "$DAC" ]; then
  echo "Could not find the DAC. Sound outputs PipeWire knows:"; pactl list short sinks
  exit 1
fi
echo "DAC = $DAC"
pactl list short sinks | grep -q "$DAC" || echo "(warning: $DAC is not listed right now)"

echo "== 3. Bass filter"
mkdir -p "$(dirname "$CONF")"
sed "s|DAC_SINK_NAME|$DAC|" "$DIR/jukebox-bass.conf" > "$CONF"
systemctl --user restart pipewire pipewire-pulse wireplumber
sleep 3
pactl set-default-sink jukebox_bass
# the launcher sets this to 100%; do the same for the DAC behind it
wpctl set-volume @DEFAULT_AUDIO_SINK@ 1.0 >/dev/null 2>&1 || true
echo "Default output is now: $(pactl get-default-sink)"

echo "== 4. Knob service"
id -nG | grep -qw input || { sudo usermod -aG input "$USER"; echo "(added $USER to the input group)"; }
mkdir -p "$HOME/.config/systemd/user"
cp "$DIR/jukebox-bass.service" "$HOME/.config/systemd/user/"
systemctl --user daemon-reload
systemctl --user enable --now jukebox-bass.service
sleep 2
systemctl --user --no-pager status jukebox-bass.service | head -8 || true

echo
echo "Done. Reboot now so Fruitbox starts on the new output:  sudo reboot"
echo "Test after reboot:  python3 $DIR/jukebox-bass.py --set 8   (then --set 0)"
