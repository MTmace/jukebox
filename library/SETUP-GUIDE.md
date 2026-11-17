# Jukebox music library: step-by-step setup

About 30 minutes. You need the Windows PC that shares the music and the Pi, both on the
same network. Do the Fruitbox setup (`../Fruitbox/fruitbox-setup/README.md`) first, or along with step 4.

---

## Step 1. Windows: share the music folder (read-only)

1. In File Explorer, right-click your music folder > **Properties** > **Sharing** tab >
   **Advanced Sharing**.
2. Tick **Share this folder**. Share name: `Music` (no spaces is easiest).
3. **Permissions**: make sure your Windows user has **Read**. You don't need Change or
   Full Control; the jukebox only reads.
4. OK, OK, Close.

## Step 2. Windows: write down three things

Open **Command Prompt** (Start, type `cmd`) and run:

```
ipconfig
whoami
```

- **PC address**: the `IPv4 Address` line, e.g. `192.168.1.20`.
  Tip: reserve this address for the PC in your router's DHCP settings so it never changes.
- **Windows user**: the part after the backslash in `whoami`, e.g. `andrew`.
  If you sign in to Windows with a Microsoft account, use that **email address** as the
  user, and its **password** (not your PIN).
- The share path is then `//192.168.1.20/Music`.

## Step 3. Copy the setup files to the Pi

On the Windows PC, download the repo from GitHub (github.com/MTmace/Jukebox, green
**Code** button, **Download ZIP**) and unzip it. Make a folder called `jukebox-setup` and copy
in the repo's `Fruitbox\fruitbox-setup` folder (renamed to `fruitbox`) and its `library`
folder, so it looks like this:

```
jukebox-setup\fruitbox\...   (fruitbox.ini, install-autostart.sh, launch-fruitbox.sh, ...)
jukebox-setup\library\...    (playlist_library.py, update-jukebox.sh, setup-share.sh, ...)
```

Then copy the folder to the Pi from Command Prompt (Windows 10/11 has `scp` built in;
use your Pi's username and hostname from Raspberry Pi Imager, default host `raspberrypi.local`):

```
scp -r jukebox-setup PIUSER@raspberrypi.local:~
```

(A USB stick works too: copy `jukebox-setup` to the Pi's home folder.)

## Step 4. Pi: Fruitbox setup (skip if already done)

On the Pi, open a Terminal (or `ssh PIUSER@raspberrypi.local` from Windows):

```bash
bash ~/jukebox-setup/fruitbox/install-autostart.sh
```

## Step 5. Pi: connect the share and install the cron job

```bash
bash ~/jukebox-setup/library/setup-share.sh //192.168.1.20/Music andrew
```

Use your own address and user from step 2. It asks for your Pi password (for sudo), then
your Windows password. It should end with lines like:

```
share mounted at /mnt/music: 42 top-level folders
cron installed:
30 3 * * * bash /home/PIUSER/fruitbox/update-jukebox.sh
@reboot sleep 120 && bash /home/PIUSER/fruitbox/update-jukebox.sh
```

If `ls /mnt/music` shows your music folders, the share works.

## Step 6. Windows: make the playlists

In PlexMediaToolkit's **Jukebox** page, make one playlist per category and save them in the
share's `_Jukebox` folder. The number at the front of each name sets the order on the genre
button, e.g. `01 Country.m3u8`, `02 Saturday Night.m3u8`. See [README.md](README.md).

## Step 7. Pi: preview, then build

```bash
python3 ~/fruitbox/playlist_library.py --dry-run
```

This lists your playlists, their song counts and the lines it would write to fruitbox.ini,
and changes nothing. The first run reads every song's tags over the network, so a big
library can take several minutes. If it looks right:

```bash
bash ~/fruitbox/update-jukebox.sh --always
tail -n 30 ~/fruitbox/library.log
ls ~/JukeboxGroups
```

## Step 8. Pi: reboot and check Fruitbox

```bash
sudo reboot
```

Fruitbox should start with only your playlist songs, and the genre button should step
through your playlists in order.

## After that

Change the playlists on Windows whenever you like. The Pi picks up changes at 3:30 every
night and 2 minutes after each boot. To update right away:
`bash ~/fruitbox/update-jukebox.sh`, then reboot.

## If something goes wrong

| What you see | Fix |
|---|---|
| `mount error(13): Permission denied` | Wrong Windows user or password. Re-run step 5. For a Microsoft account use the email address. |
| `mount error(112)` or `Host is down` | Wrong PC address, PC asleep, or file sharing off (Settings > Network > Advanced sharing > turn on file sharing, Private network). |
| `/mnt/music is not mounted` in the log | The PC was off at run time. Nothing changed; it retries next night. |
| `would remove N of M songs, over the 50% limit` | A playlist was emptied or the share was half visible. Check, then run `bash ~/fruitbox/update-jukebox.sh --force` once if the drop is real. |
| no `_Jukebox` folder found | Save at least one playlist from PlexMediaToolkit's Jukebox page first. |
