#!/usr/bin/env bash
# One-time setup: tells the Pi's display system (X11) the jukebox screen layout,
# so both screens come up right at every boot, before anything else starts.
#   HDMI-1 = 34" ultrawide, 3440x1440, left, primary (Fruitbox screen 1),
#            turned upside down (Rotate inverted) because it is mounted that way
#   HDMI-2 = bar screen,    2560x720,  to its right  (Fruitbox screen 2)
# The 2560x720 mode is written in by hand, so it works even when the bar
# screen doesn't report its sizes at boot.
#
# Run as your normal user:   bash /home/mtmace/fruitbox/setup-screens.sh
# then reboot. To undo:      sudo rm /etc/X11/xorg.conf.d/20-jukebox-screens.conf
set -euo pipefail

CONF=/etc/X11/xorg.conf.d/20-jukebox-screens.conf
sudo mkdir -p /etc/X11/xorg.conf.d
sudo tee "$CONF" >/dev/null <<'EOF'
# Jukebox screen layout (from setup-screens.sh). Monitor sections are matched
# to outputs by name. Delete this file to go back to automatic layout.
Section "Monitor"
  Identifier "HDMI-1"
  Option "PreferredMode" "3440x1440"
  Option "Position" "0 0"
  Option "Primary" "true"
  Option "Rotate" "inverted"
EndSection

Section "Monitor"
  Identifier "HDMI-2"
  Modeline "2560x720" 119.0 2560 2608 2640 2720 720 723 728 730 +hsync -vsync
  Option "PreferredMode" "2560x720"
  Option "Position" "3440 0"
EndSection
EOF
echo "Wrote $CONF. Reboot to use it:  sudo reboot"
