#!/usr/bin/env bash
# Cron job: rebuild the jukebox's categories from the playlists made in
# PlexMediaToolkit's Jukebox page (the share's _Jukebox folder), then write the
# title-strip text. Installed to /home/mtmace/fruitbox/.
#
# Since 2026-11-04 only songs in a playlist are on the jukebox; ratings and
# genre_map.txt are no longer used (jukebox_library.py and genre_library.py
# are kept in the repo for reference but not run).
#
#   bash /home/mtmace/fruitbox/update-jukebox.sh            normal run
#   bash /home/mtmace/fruitbox/update-jukebox.sh --always   also rewrite the strip titles when nothing changed
#   bash /home/mtmace/fruitbox/update-jukebox.sh --force    allow a run that removes over half the songs
#
# The log is /home/mtmace/fruitbox/library.log; songs a playlist names but the
# share doesn't have are listed in /home/mtmace/fruitbox/playlist-missing.txt.

SHARE=/mnt/music
GROUPS_DIR="$HOME/JukeboxGroups"
FB="$HOME/fruitbox"
MODE=symlink     # change to copy if Fruitbox skips symlinked songs
LOG="$FB/library.log"

exec 9>"$FB/.library.lock"
flock -n 9 || exit 0                 # previous run still going
exec >>"$LOG" 2>&1
echo "== $(date '+%F %T')"

ALWAYS=; EXTRA=()
for arg in "$@"; do
  case "$arg" in
    --always) ALWAYS=1 ;;
    --force)  EXTRA+=(--force) ;;
  esac
done

ls "$SHARE" >/dev/null 2>&1          # wakes the automount
python3 "$FB/playlist_library.py" --share "$SHARE" --dest "$GROUPS_DIR" --mode "$MODE" \
        --ini "$FB/fruitbox.ini" --missing-log "$FB/playlist-missing.txt" "${EXTRA[@]}"
rc=$?
if [ "$rc" -eq 0 ] && [ -z "$ALWAYS" ]; then
  echo "no changes"; exit 0
fi
[ "$rc" -ne 0 ] && [ "$rc" -ne 3 ] && { echo "playlist update failed ($rc), jukebox left as it was"; exit "$rc"; }

python3 "$FB/strip_titles.py" "$GROUPS_DIR"

# Keep the log short.
tail -n 2000 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
