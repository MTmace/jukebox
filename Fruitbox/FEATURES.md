# Fruitbox v3: everything it can do

Taken from the official Fruitbox 3.02.03 user guide (the guide is only shipped inside
the Pi install package, at `/opt/fruitbox/userguide.html` on the Pi), the release notes
and the example skins at https://github.com/chundermike/fruitbox-v3. Fruitbox is closed
source, so this list is limited to what the author documents plus what we found by
testing on the Pi and in the emulator.

**The "Ours" column** shows whether our Firestar jukebox uses it today, based on the
repo files `Fruitbox/fruitbox-setup/fruitbox.ini`, `Fruitbox/fruitbox-setup/launch-fruitbox.sh`
and `Fruitbox/Skins/Firestar Ultrawide/fruitbox.cfg` (main branch, 2026-10-17).

- ✅ = we use it
- ➖ = available, we don't use it
- ⚠️ = we found a problem with it (see "Known limits" at the end)

**Two files control Fruitbox.** Think of them like Windows settings files:

- `fruitbox.ini` (ours: `/home/mtmace/fruitbox/fruitbox.ini`) holds machine settings
  that don't depend on the look: buttons, volume, credits, attract mode, music folders.
- The skin's `fruitbox.cfg` (ours: `/opt/fruitbox/skins/Firestar Ultrawide/fruitbox.cfg`)
  holds the look: screen layout, title strips, status boxes, fonts, sounds.

---

## 1. Playing music and the queue

| Feature | Setting or button | Ours |
|---|---|---|
| Plays many audio formats: aac, aiff, alac, cda, flac, m4a, m4b, mp3, mid, mpa, ogg, pcm, wav, wma | automatic | ✅ (FLAC and MP3) |
| Plays video files (mp4, mkv, avi, mov, mpg and more) as songs | automatic | ➖ |
| Plays internet radio / URL streams, and .m3u / .pls playlists as "songs" | put the playlist in a music folder | ➖ |
| Play queue ("Coming Up" list) with a size limit | ini `MaxPlayQueueLength` | ✅ 20 |
| Block a song being queued twice | skin `NoDuplicates = yes` | ✅ added in PR #16 (`NoDuplicates = Yes`), pending merge |
| Whether a duplicate pick still costs a credit | skin `DuplicatesUseCredits` | ➖ |
| Loop the queue: finished songs go back on the end | ini `LoopPlayQueue`, button LoopQueue (F11) | ➖ off |
| Instant play: a pick stops the current song and plays at once (no queue) | skin `InstantPlay` | ➖ |
| Skip the current song | button Skip (Backspace) | ✅ key works, not on the cabinet buttons |
| Pause / resume | button Pause (`;`) | ✅ key works; skin shows a PAUSED sign |
| Clear the whole queue | button ClearQueue (Delete) | ➖ not on the cabinet |
| Shuffle the queue | button ShuffleQueue (Left Alt) | ➖ |
| Random song added to the queue | button Random (Space) | ✅ glass-bar button; Teensy "fill queue" sends it 20 times |
| Avoid repeating recent songs in random and attract picks | ini `SongHistoryDepth`, `SongHistoryIncludeUserSelection` | ✅ depth 20, user picks not counted |
| Simulated record "load" and "unload" time between songs (like the mechanism moving) | skin `SongLoadTime`, `SongUnloadTime` | ✅ load 1.7 s with a record-drop sound, unload 0 |
| Albums mode: one code queues a whole album (3 styles: album as one entry, one track, all tracks) | skin `AlbumMode`, `AlbumModeType`, `SortAlbumsBy` | ➖ we use singles |
| Save the queue when Fruitbox quits and reload it next start | command line `--save-playlist`, `--load-playlist` | ➖ |
| Count of songs played and total time played | `${TOTAL_PLAYED_SONGS}`, `${TOTAL_PLAYED_TIME}` | ➖ |
| **Not available:** "play next" / jump a song to the front of the queue | none | (author would have to add it) |

## 2. Picking songs (selection and input)

| Feature | Setting or button | Ours |
|---|---|---|
| Select codes made of up to 4 characters, any mix of digits and letters | skin `SelectButtons` (one line per digit) | ✅ 3 digits: first is 1 or 2, then 0-9, 0-9 (codes 100-243) |
| Pick plays as soon as the last digit is entered, or wait for a Select key | skin `AutoSelect` | ✅ yes (no Enter needed) |
| Half-typed code clears after a pause; finished code stays on screen a while | skin `SelectTimeout`, `SelectHoldTimeout` | ✅ 10 s and 3 s |
| Hide codes on empty title-strip slots | skin `HideInvalidStripCodes` | ✅ |
| Page left / right through the title strips | buttons Left, Right (arrow keys) | ✅ glass-bar buttons |
| Jump several pages at once | buttons LeftScreen `[`, RightScreen `]`, skin `ScreenJump` | ➖ |
| Jump to the next letter of the alphabet (by the last sort field) | buttons LeftSort `,`, RightSort `.` | ➖ |
| Stop at the first/last page instead of wrapping around | skin `DisableTitleStripWrap` | ➖ wraps |
| Pages turn by themselves when idle | skin `TitleStripAutoTurnTime` | ✅ every 2 minutes |
| Every button can be a keyboard key, a Pi GPIO pin, a USB game controller, or a touch-screen area | ini `[buttons]`, or the on-screen Controls menu | ✅ keyboard keys only (the Teensy and macro pad act as USB keyboards) |
| Joystick mode: move a highlight with up/down/left/right and press Select (arcade style) | ini `[joystick]` | ➖ |
| Touch screen: tap song titles or drawn buttons | ini `[touch screen]`, skin `[touch song]`, `[touch buttons]` | ➖ (status bar touch left unplugged on purpose) |
| Mouse: works like touch | ini `[mouse]` | ➖ |
| On-screen search filter (by artist, title, year and so on) | button Search (`/`) | ➖ needs a keyboard with letters |
| On-screen main menu: settings, button mapping, download skins, about, power off | button Menu (Tab) | ✅ for setup only |
| Quit Fruitbox / power off the Pi | buttons Quit (Esc), PowerOff (SysRq) | ✅ Esc; our launcher restarts Fruitbox if it exits |
| Take a screenshot (saved as screenshot.jpg in the skin folder) | button Screenshot (Right Ctrl), skin `Screenshot` | ✅ key available |

## 3. Coins and credits

| Feature | Setting or button | Ours |
|---|---|---|
| Free play (no coins needed) | ini `FreePlay`, button FreePlay (F12) | ✅ free play on |
| Up to 6 coin inputs, each worth its own number of credits | ini `CreditsPerCoin1`..`6`, buttons Coin1..6 (F1..F6) | ➖ coin slot wiring planned on the Teensy |
| Credits per song, free credits at start, keep unused credits over a restart | ini `CreditsPerSong`, `InitialCredits`, `SaveCreditsOnExit` | ➖ |
| Clear all credits | button ClearCredits (Caps Lock) | ➖ |
| Show credits / "insert coin" messages | `${CREDITS}`, `${SONGS_CREDITED}`, `${IF_FREEPLAY}`, `${IF_NO_CREDITS}` | ✅ skin shows FREE PLAY |

## 4. Attract mode (plays songs by itself when idle)

| Feature | Setting or button | Ours |
|---|---|---|
| Play random songs when the queue is empty | ini `[attract mode] Enable`, button AttractMode (`'`) | ✅ starts Off at boot; `'` turns it on live |
| Random or in sorted order | `Choice` | ✅ random |
| Gap before the next attract song | `Interval` | ✅ 0.2 minutes (12 s) |
| Attract songs quieter than normal songs | `MaxVolume` | ✅ 100 (same volume) |
| Fade in / fade out, start part-way in, stop early (play a "preview") | `FadeIn`, `FadeOut`, `FadeInPosition`, `FadeOutPosition` | ➖ full songs |
| Skip the load/unload animation for attract songs | `SkipLoad` | ✅ yes |
| Pressing the attract button cycles Off, then each listed genre, then Any | skin `AttractModeGenre` (one line per genre) | ➖ lines present but commented out |
| Never pick certain genres in attract mode | skin `AttractModeExcludeGenre` | ➖ (our library script already leaves Christmas/Holiday out) |
| Show the current attract genre on screen | `${ATTRACT_MODE_GENRE}`, `${IF_ATTRACT_MODE}`, `${IF_ATTRACT_PLAYING}` | ✅ |
| Random picks follow the current genre group | automatic | ✅ |

## 5. Music library and database

| Feature | Setting or button | Ours |
|---|---|---|
| Music folders, searched including sub-folders | `MusicPath` (ini, skin, or command line; command line wins, then skin, then ini) | ✅ set in the ini by `genre_library.py` |
| Music groups: tag folders with group names, cycle groups with one button (max 30 groups) | `MusicPath = folder = Group name`, button MusicGroup (Right Alt) | ✅ our genre button, groups like "Country (412)" |
| Include an "All Songs" group, and rename it | ini `MusicGroupIncludeAllSongs`, `MusicGroupAllSongsLabel` | ✅ yes, "All Songs" |
| Show the current group name | `${MUSIC_GROUP}` | ✅ |
| Database file `fruitbox.db` written in each music folder, rebuilt automatically when the folder changes | automatic; `--no-database-refresh`, `--force-database-refresh` | ✅ our `strip_titles.py` writes the short titles into these files |
| fruitbox.db is plain text and can be hand-edited | | ✅ we edit it with a script |
| Copy one extra MP3 tag into the "Custom" field | ini `CustomMP3Tag` | ➖ blank; we fill Custom ourselves |
| Read artist and title from file names like "Artist - Title.mp3" | ini `ExtractArtistAndTitleFromFilename` (new in 3.02.03) | ➖ |
| Ignore "The " at the start of artist names when sorting | ini `IgnoreArtistPrefixThe` | ✅ |
| Sort songs by up to several fields, each up or down (title, artist, album, album artist, year, genre, track, publisher, ISRC, custom, random, unsorted) | skin `SortSongsBy` | ✅ by title, then artist |
| Song data available to skins: title, artist, album, album artist, year, genre, track number, publisher, ISRC, custom, length | `${SONG_*}`, `${NOW_PLAYING_*}`, `${COMING_UP_*}` | ✅ |
| Cover art from the file, from folder.jpg/cover.jpg, from a named file, or a fallback picture | skin `NowPlayingArtworkMode`, `ArtworkFilename`, `NowPlayingMissingArtwork` | ✅ auto |

## 6. Main screen look (skins)

| Feature | Setting or button | Ours |
|---|---|---|
| Skins are plain text files plus pictures, fonts and sounds in one folder | | ✅ "Firestar Ultrawide" |
| Skin chooser at start-up (with timeout), or start straight into one skin | ini `[skins]`, `SkinChooserTimeout`, `--skin` | ✅ launcher passes `--skin` |
| Download / update example skins from the menu | Menu → Download/Update Skins | ➖ |
| Skin drawn at any size and scaled to fit the screen | skin `SkinSize`, `--display-size`, `--no-scale` | ✅ 3440x1440 |
| Title strips: how many songs per strip, size, background picture | `SongsPerTitleStrip`, `TitleStripSize`, `TitleStripBackground` | ✅ 2 songs per strip, 72 strips on screen |
| Different strip background per genre | `TitleStripBackground = file.png Genre` | ✅ Firestar colours per genre |
| Two songs on one strip like an A/B side, sharing the artist line | `PairSongs = yes/dual` | ✅ dual |
| Choose what text goes on each strip line (fixed text mixed with song fields) | `SongDescription`, `PairedSongDescription`, `ArtistDescription`, `MatchedArtistDescription`, `ExtraDescription` | ✅ short title from Custom, artist(s), strip codes |
| Text styles: font, colour, alignment, all caps, squash-to-fit or scroll, quotes, offset, max width | `SongText`, `ArtistText`, `ExtraText` and so on | ✅ squash-to-fit on strips |
| Page-turn animations: swipe, reveal, turn, dissolve, spin, carousel (book page), with speed and fade | `TitleStripMoveStyle` | ✅ effect 4 (turn horizontally), speed 50 |
| Stagger the page turn strip by strip (ripple effect) | `[title strip] MoveDelay`, `MoveLeftDelay`, `MoveRightDelay` | ✅ ripple across columns |
| Cover art on each song in the title strips | `TitleStripArtworkSize`, `TitleStripArtworkMode` | ➖ |
| Pictures, status boxes, spectrum, level meters and lyrics can be placed anywhere, any number of them, drawn in file order | `[bitmap]`, `[status]`, `[spectrum]`, `[level]`, `[lyrics]` | ✅ 3 pictures, 28 status boxes, 4 spectrum bars |
| Rotate, tilt in 3D, flip, colour-tint and crop any object | `Angle`, `Perspective`, `XAxisOffset`.., `HorizontalFlip`, `Tint`, `Clip` | ✅ crop used for the volume meter |
| Moving objects: size/position/colour/crop that follow volume, music level, elapsed time, queue size, a timer or random | dynamic values `[max ${VOLUME}]` etc. | ✅ volume meter on the bar screen |
| Load any TrueType/OpenType fonts | skin `[fonts]` | ✅ Anton, DejaVu and others |
| Print real paper title strips: writes every strip to a PNG and quits | command line `--dump-title-strips` | ➖ (handy if we ever want paper strips) |
| Show each song's select code (for skin testing) | command line `--debug-song-nums` | ➖ |

## 7. Status boxes (text and pictures that change live)

Status boxes are the "smart" parts of a skin: Now Playing, Coming Up, the select digits,
credits, the clock, and so on. Each box reads a small text file of instructions.

| Feature | Setting or button | Ours |
|---|---|---|
| Show now-playing details, elapsed / remaining time, album time | `${NOW_PLAYING_*}` | ✅ |
| Show the Coming Up list, song count and total time | `${COMING_UP_*}`, `${COMING_UP_NUM_SONGS}`, `${COMING_UP_TOTAL_TIME}` | ✅ both screens |
| Show the last song played | `${LAST_PLAYED_*}` | ⚠️ crashes Fruitbox |
| Show the code being typed | `${SELECT_CODE}` | ✅ red 7-segment digits |
| Show volume / mute | `${VOLUME}`, `${IF_MUTE}` | ✅ volume meter on the bar screen |
| If / else conditions on almost everything: playing, paused, loading, queue empty/full, attract, invalid or duplicate pick, each button pressed, page turning, mute, credits | `${IF_...}`, `${ELSE}`, `${END_IF}` | ✅ |
| Cover art in a box | `${NOW_PLAYING_ARTWORK}` | ✅ |
| Pictures and animations (flip through many pictures on a timer), or a slideshow folder | `Bitmap`, `FileDirectory`, `${DRAW_BITMAP}`, timers | ✅ light-bar animation |
| Sound effects on any event (page turn, key press, coin, record load) | `Sound`, `${PLAY_SOUND}` | ✅ page turn, key press, record drop |
| Decorative video clips, or the music video itself, in a box | `Video`, `${DRAW_VIDEO}` | ➖ |
| Audio visualiser pictures for audio songs (oscilloscope, Synaescope, spectrum scope, stereo, GOOM) | skin `AudioVisualiser` | ➖ |
| Per-box timers (blink, scroll speed, one-shot, start delay) | `TimerTickPeriod`, `TimerOneShot`, `TimerStartDelay` | ✅ |
| Text scrolling for long titles | text mode 1..n | ✅ bar screen Now Playing |
| Four on/off flags that boxes and buttons can share (for example, a button that shows a hidden panel) | `Flag1`..`Flag4` buttons (F7..F10), `${SET_FLAG_n_HI}`, `${IF_FLAG_n_HI}` | ➖ (could drive a hidden "service" panel) |
| Write a box's text to a file for other programs to read | `Output = file` | ✅ `/dev/shm/jukebox_state.txt` drives the cabinet lights bridge |
| Run once at start-up | `Initial` | ✅ |

## 8. Second screen and networked screens

| Feature | Setting or button | Ours |
|---|---|---|
| Use more than one monitor from one Fruitbox, each with its own size | skin `SkinSize = 2 w h`, `DisplayNumber = 2` on objects | ✅ 2560x720 status bar screen |
| Multicast transmit: send the music, video and status over the home network | ini `[multicast] Mode = Transmit` | ➖ |
| Multicast receive: another Pi plays and shows what the main jukebox is doing (a remote screen or speaker) | `Mode = Receive` | ➖ (the way to get a 3rd screen) |

## 9. Sound and volume

| Feature | Setting or button | Ours |
|---|---|---|
| Fruitbox's own volume, start level and step size | ini `SongVolume`, `SongVolumeStep`, buttons VolUp `=`, VolDown `-` | ✅ starts at 5 (one step above silent), steps of 5, macro pad knob |
| Mute | button Mute (Left Ctrl) | ➖ |
| Even out loudness between songs using ReplayGain tags already in the files (per track or per album) | ini `ReplayGain` | ➖ (only helps if the files are tagged) |
| Spectrum analyser, up to 32 bands, left/right/both, peak decay | skin `[spectrum]` | ✅ footer and bar screen |
| Level / waveform meter | skin `[level]` | ➖ |
| Line up the meters with the sound | ini `SpectrumAudioSyncOffset` | ✅ 0 |

## 10. Karaoke lyrics

| Feature | Setting or button | Ours |
|---|---|---|
| Shows timed lyrics from a `.lrc` file with the same name as the song, with highlighted current line and male/female/duet colours | skin `[lyrics]` | ➖ |

## 11. Raspberry Pi GPIO pins (wires straight to the Pi)

| Feature | Setting or button | Ours |
|---|---|---|
| Any button can be a switch wired between a Pi GPIO pin and ground (normally-open or normally-closed, auto-detected) | ini `[buttons]` | ➖ we use the Teensy as a USB keyboard instead |
| Turn GPIO pins 0-27 on/off from status boxes (lamps, relays, "now playing" lights) | `${SET_GPIO_nn_HI}` / `_LO` | ➖ lights are driven from the Teensy and the WLED bridge |
| Note: pins used by the DAC HAT (for example GPIO 18 and the other I2S pins) can't be used | | applies to our InnoMaker DAC |

## 12. Command line options (what the launcher can pass)

| Option | What it does | Ours |
|---|---|---|
| `--ini file` | Use a specific settings file | ✅ |
| `--skin file` | Start straight into one skin | ✅ |
| `--log file`, `--debug` | Write a log, with extra detail | ✅ log |
| `--music-path folder` | Override the music folders | ➖ |
| `--no-database-refresh`, `--force-database-refresh` | Skip or force the music database rebuild | ➖ |
| `--load-playlist`, `--save-playlist` | Restore the queue across restarts | ➖ |
| `--display-size n w h x y windowed` | Force a screen size or a window | ➖ (the launcher sets screens with xrandr) |
| `--no-scale`, `--debug-song-nums`, `--dump-title-strips`, `--user-guide`, `--version` | Testing and printing tools | ➖ |

## 13. Default keyboard keys

These are the stock keys. Our Teensy keypad sends the digits, the glass bar and macro pad
send Left, Right, Right Alt, Space and `=`/`-`.

| Key | Does | Key | Does |
|---|---|---|---|
| Left / Right arrows | Page left / right | `[` / `]` | Jump pages |
| `,` / `.` | Previous / next letter | Up / Down | Joystick mode only |
| 0-9, A-Z | Select code characters | Enter | Select (when AutoSelect is off) |
| Space | Random song | Backspace | Skip song |
| `;` | Pause | `'` | Attract mode on/off (or next genre) |
| F1-F6 | Coins 1-6 | Caps Lock | Clear credits |
| F7-F10 | Flags 1-4 | F11 | Loop queue on/off |
| F12 | Free play on/off | Delete | Clear queue |
| Left Alt | Shuffle queue | Right Alt | Next music group (our genre button) |
| `=` / `-` | Volume up / down | Left Ctrl | Mute |
| Right Ctrl | Screenshot | `/` | Search menu |
| Tab | Main menu | Esc | Quit |
| SysRq | Power off the Pi | | |

---

## Known limits (found by us, not in the guide)

- **No "play next".** There is no way to put a pick at the front of the queue. Only the author can add it.
- **Attract songs aren't interrupted.** A real pick waits for the attract song to finish. Workarounds: shorter attract previews (`FadeOutPosition`) or Skip.
- **`${LAST_PLAYED_*}` crashes Fruitbox** at start-up (3.02.02), so we never use it.
- **A second-screen status box with a `Bitmap` line stops Fruitbox** if the second monitor isn't plugged in. Plain `[bitmap]` objects on screen 2 are fine.
- **Now Playing shows the file's own tags.** While a song plays, title, artist, album, year, genre, ISRC and publisher come from the file's tags, not fruitbox.db. Only the Custom field always comes from fruitbox.db, so it's the only safe place for our short titles.
- **Coming Up uses one shared "cursor" per field.** Each `${COMING_UP_...}` field steps to the next song every time it's used, across all boxes in the skin, so two lists using the same field split the queue between them.
- **Scrolling text has no pause** before it starts, and its speed is tied to the box's timer.
- **Under Wayland both windows land on the ultrawide.** The Pi has to run X11 (raspi-config → Advanced → Wayland → X11).
- **Volume readout only tracks Fruitbox's own volume** (`=` / `-`), not the Pi's system volume.
