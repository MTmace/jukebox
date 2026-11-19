#!/usr/bin/env bash
# One-time Pi setup: mount the Windows music share read-only at /mnt/music,
# install the library scripts to ~/fruitbox/, and add the cron job.
#
#   bash setup-share.sh //192.168.1.20/Music  WINDOWS_USER
#
# Run as the normal user (pi), not with sudo; it asks for sudo where needed.
set -euo pipefail

SHARE_UNC="${1:?usage: setup-share.sh //SERVER/Share WINDOWS_USER}"
WIN_USER="${2:?usage: setup-share.sh //SERVER/Share WINDOWS_USER}"
MOUNT=/mnt/music
CRED=/etc/jukebox-share.cred
HERE="$(cd "$(dirname "$0")" && pwd)"
FB="$HOME/fruitbox"

sudo apt-get install -y cifs-utils python3-mutagen

read -rsp "Windows password for $WIN_USER: " WIN_PASS; echo
printf 'username=%s\npassword=%s\n' "$WIN_USER" "$WIN_PASS" | sudo tee "$CRED" >/dev/null
sudo chmod 600 "$CRED"
unset WIN_PASS

sudo mkdir -p "$MOUNT"
# ro: the jukebox never writes to your library.  nofail + automount: boot
# carries on if the PC is off; the share mounts on first use.
OPTS="credentials=$CRED,ro,uid=$(id -u),gid=$(id -g),iocharset=utf8,vers=3.0,_netdev,nofail,x-systemd.automount,x-systemd.mount-timeout=30"
LINE="$SHARE_UNC $MOUNT cifs $OPTS 0 0"
# Re-running replaces our earlier line, so a wrong address or user can be fixed.
sudo cp /etc/fstab /etc/fstab.bak
grep -vE "^[^#]*[[:space:]]$MOUNT[[:space:]]" /etc/fstab.bak | sudo tee /etc/fstab >/dev/null
echo "$LINE" | sudo tee -a /etc/fstab >/dev/null
sudo umount "$MOUNT" 2>/dev/null || true
sudo systemctl daemon-reload
sudo systemctl restart remote-fs.target || true
if ! ls "$MOUNT" >/dev/null 2>&1; then
  echo "Could not open $SHARE_UNC. Check the PC address, user and password, then re-run."
  echo "Details: sudo dmesg | grep -i cifs | tail"
  exit 1
fi
echo "share mounted at $MOUNT: $(ls "$MOUNT" | wc -l) top-level folders"

mkdir -p "$FB"
install -m 755 "$HERE/music_tags.py" "$HERE/playlist_library.py" "$HERE/update-jukebox.sh" "$HERE/strip_titles.py" "$FB/"

# Nightly at 3:30, and 2 minutes after each boot.  Every 4 minutes, list the
# share so Windows doesn't drop the idle connection (it does after 15 min);
# otherwise the first song picked after a quiet spell waits seconds while the
# Pi reconnects, and the jukebox seems to ignore the third digit.
( crontab -l 2>/dev/null | grep -v -e update-jukebox.sh -e "ls $MOUNT" || true
  echo "30 3 * * * $FB/update-jukebox.sh"
  echo "@reboot sleep 120 && $FB/update-jukebox.sh"
  echo "*/4 * * * * ls $MOUNT >/dev/null 2>&1"
) | crontab -
echo "cron installed:"; crontab -l | grep -e update-jukebox.sh -e "ls $MOUNT"

echo
echo "Next: preview the playlists, then do the first build:"
echo "  python3 $FB/playlist_library.py --dry-run"
echo "  $FB/update-jukebox.sh --always && tail $FB/library.log"
