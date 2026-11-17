# Cabinet lights

LED strips around the cabinet, driven straight from the Pi. A small program on the
Pi (`cabinet-lights/jukebox-bridge.py`) watches what the jukebox is doing and
plays a matching light pattern on the Pi's pins.
(It can still drive a WLED controller instead, see the end of this page.)

The 22 selection numbers are separate: the Teensy drives those
(`arduino/SELECTION-LIGHTS.md`).

Status: tested on a PC (the patterns, the signal bytes, the state switching, the
dimmer and themes, the per-strip scenes, and the beat detection with a test drum
track). Not yet run on
the Pi or real strips, the keyboard controls haven't been tried with a real
keyboard or knob, and the music capture hasn't been tried with Fruitbox.

## The strips

Four 40" strips (52, 55, 53 and 46 LEDs, 206 in all), all **one chain on one Pi
pin**: the data goes along the window strip, on into the subs strip (flipped, so
it comes back the other way), on into the upper strip that shines up the wire
mesh, and last into the white panel strip. Only two wires go to the Pi: data on
pin 32 and GND on pin 34. The program still treats each strip separately, so the
fire strips can run different animations and chase each other while the white
one stays white.

| Strip | Chain | Pi pin | What it shows |
|---|---|---|---|
| **window**: front, shining up at the window | 1st, data in at its left end | Physical pin 32 (GPIO 12) | The theme |
| **subs**: front, under it, lighting the subs | 2nd, flipped: data runs right to left | (from the window strip's DOUT) | The theme |
| **third**: upper, shining up the wire mesh | 3rd | (from the subs strip's DOUT) | The theme |
| **white**: behind the selection panel and keys | 4th, last | (from the upper strip's DOUT) | Steady white |

Each strip still gets its own fused power pair from the supply, all fed from the
same side; only the data is chained. The jumper between strips is three wires
(5 V, data, GND) joined in the chain, or just data (DOUT to the next DIN) plus
GND when each strip has its own power feed.

Different chain order? Change `chain =` (and `reverse =` for a strip the data
runs through from right to left) in the strip's section of the settings. Strips
on separate pins also work: give each its own `device` and its own
`dtoverlay=ws2812-pio` line (pins 15, 16 and 18 are free, GPIO 22, 23 and 24).

Pin 32 isn't used by the DAC HAT (it uses GPIO 18-21 for sound and 2-3
for its volume chip).

The guide used pin 19 (GPIO 10) until 2026-11-11, when that pin on this
Pi stopped working (told to switch on with `pinctrl`, it still read `lo`).
If you're on pin 19 and the strips stop responding, test it the same way:
`sudo pinctrl set 10 op dh; pinctrl get 10` should end in `hi`. Reboot after
any `pinctrl` test to hand the pin back to the lights. Never touch the data
wire to 5 V while it's plugged into the Pi: that can kill the pin.

## What the lights do

The lights follow the jukebox's one state, decided by the state manager
(`state-manager/jukebox-state.py`, which writes it to `/dev/shm/jukebox_mode`).
Each theme decides how each state looks:

| Jukebox state | Patterned strips (Fire theme; the default White theme is steady white) | White panel strip |
|---|---|---|
| Active: a song playing, or a key, knob or coin in the last minute | `fire`: bright flickering flames, 100 % | On |
| Idle: no song and no key for a minute (also while starting up) | `candle`: soft warm flicker, 20 % | Dimmed to 20 % |
| Attract mode on | `aurora`: slow green, teal and violet waves, 35 % | Dimmed to 35 % |
| Sleep: 10 minutes idle, or the Pause key (screens off) | the theme's 4th pattern if it has one, else its idle one, 15 % | Dimmed to 15 % |
| Shutting down (Reboot, Rebuild Playlist, Shut Down keys) | off | Off |
| A coin just dropped (3 s, any state but sleep) | `sparkle`: gold sparkles | On |

If the state manager isn't running, the lights decide for themselves as
before: bright while a song plays or for 30 s after a key, dim otherwise.

**Themes** (the theme key steps through them; the white strip doesn't change):

| Theme | Idle | Active | Attract | Sleep |
|---|---|---|---|---|
| White (default) | dim white, 20 % | bright white, 100 % (doesn't pulse with the music) | white, 35 % | white, 15 % |
| Fire | candle | fire, each strip flickering on its own | aurora | candle |
| Rising | candle | flames start on the bottom strip and climb into the ones above, a moment later and a little cooler; a burst on a bass hit climbs from the subs up to the window | flow | candle |
| Relay | candle | fireballs run along the top strip, drop to the next one and run back, and so on down to the subs strip, over a glow of embers; every beat sends a new one (without music, one every 2.5 s) | flow | candle |
| Duet | candle | the strips take turns: one burns bright while the others drop to embers, swapping on every beat (every 1.5 s without music) | flow | candle |
| VU | slow red glow | music meter: lights grow from the middle with the beat, lime to red | aurora | slow red glow |
| Firestar | slow red glow | red, yellow and lime bands drifting | aurora | slow red glow |
| Lava | lava | lava (deep red and orange blobs) | aurora | lava |
| Ocean | ocean | ocean (blue and teal swells) | aurora | ocean |
| Rainbow | slow red glow | rainbow chase | aurora | slow red glow |

Every theme shows its idle look while the jukebox starts up and goes dark when it shuts down. Sleep is the idle pattern at 15 % unless the theme line has a 4th word.

`flow` is the aurora as one long wave running through all the strips in turn,
instead of each strip on its own. The scene themes use the strips in the order
listed in `strips =` in the settings, top to bottom: the upper wire-mesh strip,
then the window strip, then the subs strip. This is separate from the chain
order, so it doesn't matter which way the data runs.
`scenes_preview.gif` shows them.

**Music:** while a song plays, the cabinet strips follow it. Their brightness
rides the bass (never below 35 %), the Fire theme throws up a burst of flames on
every beat, and the VU theme is a music meter. No microphone or sensor is needed:
the bridge listens to a copy of exactly what the Pi sends to the DAC, so it hears
the whole song, not just the subwoofer, and room noise doesn't count. It adjusts
to the song's loudness by itself, so it works at any Fruitbox volume. The white
panel strip never reacts. Turn it off or change it in `[sound]` in the settings.

**Controls** (from any keyboard, or a knob plugged into the Pi):

| Key | Does |
|---|---|
| Scroll Lock or F13 | Lights off / on (all strips) |
| Page Up or F14 | Brighter (all strips) |
| Page Down or F15 | Dimmer (all strips) |
| Insert or F16 | Next theme (cabinet strips only) |

Fruitbox uses F1-F12, so these are keys it ignores. For a dial, get a small
programmable USB knob (like the Koolertron pad's knob) and set it to send F14 /
F15 when turned and F13 when pressed. Don't use the volume or mute media keys:
the Pi's desktop would change the sound volume too. On/off, brightness and the
theme are remembered after a restart.

Everything (the patterns per theme, the brightness of each state, the white
level, the LED counts, the keys) is in `/home/mtmace/fruitbox/jukebox-bridge.ini`.
New patterns are short Python functions near the top of `jukebox-bridge.py` (ask
Claude for one).

## Parts

| Qty | Part | Notes |
|---|---|---|
| 4 | **5 V** addressable LED strips (WS2812B), 40" each, 60 LEDs per metre | Each strip's data in (DIN) wire comes back to the Pi. |
| 1 | The 40 A screw-terminal power supply, 110 V in, **5 V** out | Check the label says 5 V. Each metre of 60/m strip can draw up to about 3.6 A at full white. |
| 1 per strip | Inline blade fuse holder + 5 A fuse in the strip's + wire | 40 A into a short would melt thin wire before the supply noticed. |
| 1 per strip | 1000 uF capacitor (10 V or more) across the strip's power input | |
| 1 | 330 ohm resistor, at the Pi end of the data wire | On pin 32. |

Wiring: each strip's 5 V and GND to the supply (through a fuse on each + wire), the
supply's COM joined to a Pi GND pin, pin 32 through a 330 ohm resistor to the
window strip's DIN, and each strip's DOUT to the next one's DIN. Keep each data wire (Pi to
first strip, and each jumper between strips) under about 1 m. At 5 V the voltage drops along a strip, so feed power into both ends of
anything longer than about 2 m (most strips have spare power wires at each end
for this). The Pi keeps its own power supply; never feed it from the LED supply's
+V.

## Wiring the 5 V power supply

The supply is a metal box with a row of screw terminals and no plug. Wiring it is
like wiring a light fixture: three mains wires in, two low-voltage wires out. Do
the mains side with the cord **unplugged** the whole time.

Terminals, left to right:

| Terminal | What it is | Connect to |
|---|---|---|
| **L** | Mains live (hot) | Black wire of the power cord |
| **N** | Mains neutral | White wire of the power cord |
| **⏚** | Earth / ground | Green (or green/yellow) wire of the power cord |
| **COM** x3 | 5 V negative (all three joined inside) | Lights' GND and a Pi GND pin |
| **+V** x3 | 5 V positive (all three joined inside) | Lights' 5 V (through a fuse each) |
| **+V ADJ** | Small knob that fine-tunes the output voltage | Leave it alone |

Wire colours are for a US cord.

### Mains side (the cord)

1. Use a **3-prong** cord: a spare computer power cord works well. Cut off the
   end that would go into a computer. Don't use a 2-prong lamp cord: the metal
   case must be earthed.
2. Strip about 1.5" of the outer jacket, then about 1/4" of each inner wire.
   Crimp a **fork (spade) terminal** onto each wire so no loose strands can touch
   the next screw.
3. Black to L, white to N, green to ⏚. Tighten each screw firmly and tug each
   wire to check it's held.
4. Close the orange flip-up **terminal cover**. The L and N screws are live at
   120 V whenever it's plugged in.
5. Zip-tie the cord to the cabinet so a pull on the cord can't pull the wires out
   of the screws.
6. Screw the supply to the cabinet wood, away from where hands go when you open it.
7. Plug it into the same switched power strip as the Pi, so it turns on and off
   with everything else.

### Check it before connecting lights

With nothing on the 5 V side, plug it in. The small indicator light should come
on. Set a multimeter to DC volts and touch the red probe to +V and the black probe
to COM: it should read about 5 V (4.9 to 5.2 is fine). Unplug it again before
wiring the 5 V side.

### 5 V side (lights and the Pi)

1. Use red and black wire, 16 or 18 AWG for each strip (a 40" strip draws at most about 3.7 A). Use a separate
   +V / COM pair for each strip.
2. Red from +V, through a **5 A fuse**, to the strip's **5 V** wire (red on the
   ALITOVE bullets); black from COM to its **GND** (white on the ALITOVE bullets).
3. Put the 1000 uF capacitor across 5 V and GND where the power wires join the
   strip. The capacitor's **stripe (-)** goes to GND.
4. A thin black wire from COM to a **GND** pin on the Pi (physical pin 34, next to
   pin 32). Without this shared ground the data signal has nothing to measure
   against and the LEDs flicker or show random colours.
5. **Data chain:** pin 32 through a 330 ohm resistor to the window strip's DIN
   (data in, green on most strips). The window strip's DOUT (far end) to the
   subs strip's DIN; the subs strip's DOUT to the upper strip's DIN; the upper
   strip's DOUT to the white strip's DIN. Run a thin GND wire beside each data
   jumper. The arrows printed on a strip point away from DIN.

Your DAC HAT passes the pins through on top, so use the same pin numbers there.
Pin 1 is the corner pin nearest the SD card end, in the inner row; the inner row is
odd numbers (1, 3, 5 …) and the outer row, along the board's edge, is even
(2, 4, 6 …). Pins 32 and 34 are both on the outer row: pin 32 is the 16th pin
along it from the pin 1 end, and pin 34 the very next one. A 2-pin plug lies
along the outer row, data on 32, GND on 34.

```
              inner row   outer row
16th pair     pin 31 ○    ● pin 32      32 = data
17th pair     pin 33 ○    ● pin 34      34 = GND to supply COM

Pi pin 32 (GPIO 12) ──[330 ohm]── window DIN →→→ DOUT ─┐
                       subs DOUT ←←← DIN (flipped) ─────┘
                         └──────── upper DIN →→→ DOUT ─┐
                                   white DIN →→→ DOUT (end) ┘
Pi pin 34 (GND) ───────────────── supply COM
supply +V ──[5 A fuse]── each strip's 5 V (red), one fuse per strip
supply COM ───────────────────────── each strip's GND (white)
```

5 V can't shock you, but a short between +V and COM can melt wires, so keep bare
ends short and covered.

## Set up the Pi

Type these one at a time in the Pi's terminal. The files from this folder go in
`/home/mtmace/Downloads/` first.

1. **Turn pin 32 into an LED pin.** The Pi 5 has a built-in LED driver that
   can run a strip (or a chain of strips) from any pin. Open the settings file
   (like Notepad):

   ```
   sudo nano /boot/firmware/config.txt
   ```

   Add this line at the bottom (`num_leds` is all the LEDs in the chain:
   52 + 55 + 53 + 46 = 206), then Ctrl+O, Enter to save and Ctrl+X to exit:

   ```
   dtoverlay=ws2812-pio,gpio=12,num_leds=206,brightness=0,dev_name=leds-fire,rgbw=on
   ```

   `rgbw=on` is for your 4-colour strips (a white chip in each LED). Without it
   the colours come out as a repeating blue, white, red pattern. For plain RGB
   strips, leave it off and set `rgbw = no` in the settings.

   If you already added a `gpio=24` (`leds-white`) line, delete it.

   If you added `dtparam=spi=on` or `dtoverlay=spi5-1cs` from an earlier version
   of this guide, put a `#` in front of both: SPI would grab pin 19, the
   old data pin. (`spidev.bufsiz=65536` in cmdline.txt can stay; it does
   nothing now.)

2. Restart the Pi: `sudo reboot`. Then check the pin is ready:

   ```
   ls /dev/leds*
   ```

   It should list `/dev/leds-fire`. If it says "No such file", check the overlay is on your Pi
   with `ls /boot/firmware/overlays/ws2812-pio.dtbo`; if that's missing, update
   the Pi (`sudo apt update && sudo apt full-upgrade`, then reboot) and try again.
   `dmesg | grep -i ws2812` shows which pins it set up.

3. Install the program, its settings and its service:

   ```
   sudo apt install python3-serial python3-evdev pulseaudio-utils
   sudo cp /home/mtmace/Downloads/jukebox-bridge.py /usr/local/bin/
   cp /home/mtmace/Downloads/jukebox-bridge.ini /home/mtmace/fruitbox/
   sudo cp /home/mtmace/Downloads/jukebox-bridge.service /etc/systemd/system/
   ```

4. Check the strip LED counts, chain order, `reverse`, and colour order in the
   settings:
   `nano /home/mtmace/fruitbox/jukebox-bridge.ini`

5. **Test the strips.** This shows every theme's idle, active and attract patterns
   for 6 seconds each, then a coin sparkle, then turns them off:

   ```
   sudo python3 /usr/local/bin/jukebox-bridge.py --demo
   ```

   Red and green swapped? Change `color_order` (GRB to RGB) in the settings.

6. Start it for good (it also starts at every boot):

   ```
   sudo systemctl enable --now jukebox-bridge
   ```

If you installed the old `knob-volume` service earlier, turn it off, because only
one program can read the Teensy at a time:

```
sudo systemctl disable --now knob-volume
```

Check it's working (Ctrl+C to stop watching):

```
journalctl -u jukebox-bridge -f
```

You should see `fruitbox: playing` / `idle` and `LEDs playing -> fire` lines as
songs start and stop, an `event:` line for every key press, and
`sound: listening to the Pi's output`. After changing the settings:
`sudo systemctl restart jukebox-bridge`.

If the lights don't move with the music, check that the Pi can hear its own
output while a song plays (Ctrl+C to stop; it should print a stream of
characters, not nothing):

```
parec -d @DEFAULT_MONITOR@ --raw | head -c 2000 | od | head
```

If `journalctl` keeps showing `sound: capture stopped`, check your user number
with `id -u mtmace`; if it isn't 1000, change `/run/user/1000` in `[sound]`.

## The Fruitbox part

The Firestar Ultrawide skin's `fruitbox.cfg` has a hidden `[status]` box (no
`Size`, so nothing is drawn) that writes the jukebox state to
`/dev/shm/jukebox_state.txt` once a second. `/dev/shm` is in memory, so it
doesn't wear out the USB drive. The contents come from `lights_state.txt` in the
skin folder:

```
PLAYING or IDLE
ATTRACT_SONG or USER_SONG
ATTRACT_ON or ATTRACT_OFF
```

`build_skin.py` writes both, so they survive a skin rebuild. To check it on the
Pi while Fruitbox runs: `cat /dev/shm/jukebox_state.txt`.

## Optional: WLED instead

The bridge can also switch presets on a WLED controller (an ESP32 on Wi-Fi). Flash
WLED from **install.wled.me**, set its mDNS name to `wled-jukebox`, make presets 1
to 5 (idle, playing, selecting, coin, attract), then in the settings set
`[wled] enabled = yes` and `[leds] enabled = no`.
