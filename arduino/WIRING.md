# Seeburg USC2 keypad, coins and lights to a Teensy 4.1

The Teensy 4.1 plugs into the Pi 5 by USB and shows up as a keyboard. Every
button press becomes the key Fruitbox already listens for, so Fruitbox needs no
button remapping. The program is `seeburg_keypad/seeburg_keypad.ino` (with
`lights.h` beside it). It compiles cleanly for the Teensy 4.1 but has not been
run on hardware yet.

New to this? Start with [KEYPAD-BEGINNER-GUIDE.md](KEYPAD-BEGINNER-GUIDE.md).

## The one rule: 3.3 V only

Teensy 4.1 pins work at **3.3 V**. Never connect 5 V or VIN to any numbered pin.
Every switch here simply connects a pin to **GND**, which is always safe.

## How the original keypad works

- **10 number keys, 0 to 9, plus Left RESET and Right RESET.** They page the
  title strips left and right. Left RESET has its own wire to Teensy pin 24
  (section 3a). Every selection is 3 digits; the
  Firestar skin uses codes **1xx and 2xx with tens digit 0-7 (row) and ones
  digit 0-8 (column)**, e.g. 100-108 ... 170-178 and 200-208 ... 270-278 (A and
  B side of each of its 72 strips). The program types each digit that can still make
  one of those codes as soon as it is pressed.
- The keypad is a Seeburg **Microlog** keypad: a gold-finger contact board plus
  a small silver-finger board on the back, joined by the original harness (two
  card-edge sockets wired together). The harness has **13 loose wires**, and those
  go to the Teensy. Each key joins one, two or three pairs of them. Testing found
  the pairs with `keypad_mapper` (2026-10-29); they are in the `KEYS` table in
  the program (table below).
- **The keys may latch.** If yours stay down until a reset solenoid releases them,
  the Teensy can fire that solenoid through a MOSFET after the third digit
  (section 6). If they spring back on their own, ignore the solenoid.

## 1. Safety first: isolate everything

The cabinet has 120 V mains and roughly 25 V AC selection and solenoid circuits.
**Unplug the jukebox.** Then disconnect the keyboard and the coin switches from
the Seeburg harness completely, by unplugging or cutting and labelling the wires.
Nothing from the original wiring may stay connected to a contact you use for the
Teensy. The Teensy inputs should only ever see their own ground and the switch.

## 2. Parts

See [`PARTS.md`](../PARTS.md) for exact items and what is bought.

| Qty | Part | Notes |
|---|---|---|
| 1 | **Teensy 4.1 with pins** (PJRC) | Not the 4.0, and not the "without pins" version. |
| 1 | USB cable, micro-USB to USB-A, **data** type | Teensy 4.1 has a micro-USB socket. Also powers the Teensy. |
| optional | Victory Glass 63-7234 keypad contact board | Only if the original board's contacts get unreliable; the original tested fine. Wires solder to the board's fingers either way. |
| about 30 | Wire (22 to 28 AWG); a 20-wire ribbon cable is tidy for the keypad | |
| optional | Logic-level N-MOSFET (IRLZ44N or IRLB8721), 1N4007 diode, 220 ohm + 10 k resistors, 24 V DC supply | For the keyboard reset solenoid (section 6). |

Software: install the **Arduino IDE 2** and **Teensyduino** (PJRC's add-on), then
the **Adafruit NeoPixel** library from the Library Manager. In the IDE choose
**Tools > Board > Teensy 4.1** and **Tools > USB Type > Serial + Keyboard + Mouse
+ Joystick**. Without that USB Type, the keys won't type.

## 3. Keypad to the Teensy

Keep both harness sockets plugged onto their keypad boards. Label the harness's
13 loose wires 1 to 13 and screw each into its own Teensy terminal. Nothing else
connects to the keypad; it needs no power.

| Harness wires | Teensy pins |
|---|---|
| 1 to 13 | **0 to 12** (wire 1 to pin 0, wire 2 to pin 1, …) |

Keep the same labels you used for the mapper test, or every key will be wrong.
Pins 24 to 30 are free for the keypad if more wires are ever needed.

The wire pairs each key joins, from `keypad_mapper`. Some keys share a pair (3's
4-10 is also part of 4, 5 and 6), so when several keys match, the program picks
the one with more matching pairs. The `KEYS` table uses the pairs in bold.

| Key | Wires joined | Key sent | Fruitbox button |
|---|---|---|---|
| 0 | **8-10** | `0` | Select digit |
| 1 | **3-10, 3-13** | `1` | Select digit |
| 2 | **9-10, 9-13** | `2` | Select digit |
| 3 | **4-10** | `3` | Select digit |
| 4 | **4-8**, 4-10, **8-10** | `4` | Select digit |
| 5 | **4-9**, 4-10, **9-10** | `5` | Select digit |
| 6 | **3-4**, 3-10, **4-10** | `6` | Select digit |
| 7 | **3-8**, 3-10, **8-10** | `7` | Select digit |
| 8 | **3-5**, 3-9, **5-9** | `8` | Select digit |
| 9 | **5-8**, 5-9, **8-9** | `9` | Select digit |
| Left RESET | **1-14, 2-14** (14 = its own wire on pin 24) | Left arrow | Pages the title strips left |
| Right RESET | **1-7, 2-7** | Right arrow | Pages the title strips right |

A key only types once its contacts have been steady for 40 ms
(`KEYPAD_SETTLE_MS`), so a key whose two contacts close a moment apart isn't
read as a different key first. One press types one key: once a key has typed,
nothing else types until every contact opens. 0 and 3 join only one pair, which
is also the first contact of 4 to 7 closing on a slow press, so they type after
150 ms held (`KEYPAD_SINGLE_MS`) or when released, whichever is first.

Digits are checked place by place: hundreds 1-2, tens 0-7, ones 0-9. A digit
that doesn't fit its place is ignored; the selection lamps blink and the keypad
waits for a valid digit in the same place. Each valid digit is typed to
Fruitbox as soon as it is pressed; ignored digits are never typed. A half-typed
selection clears after 10 s with no valid digit, on the Teensy and in Fruitbox
(the skin's `SelectTimeout`), so the two stay in step. Keep
`PENDING_TIMEOUT_MS` equal to `SelectTimeout` if you change either.

### 3a. Telling the two RESET keys apart (done 2026-10-29)

On the original board both RESET keys join wires 1-7 and 2-7. Wires 1 and 2 are
joined on the board, so each RESET key is really one switch between "1/2" and
"7", and cutting one of the pairs isn't possible. Instead:

1. Cut the bottom track that carries wire 7 from Left RESET's contacts past
   Right RESET to the harness, between the two keys. Right RESET keeps wire 7.
2. Solder a wire onto that track on Left RESET's side of the cut, away from the
   contact pads, and run it to Teensy pin 24 (keypad_mapper calls it "14").

keypad_mapper then shows Left RESET = 1-14 2-14 and Right RESET = 1-7 2-7.

## 4. Coin slot and buttons

Each switch goes between its pin and **GND**.

| Teensy pin | Connect to | Key sent | Fruitbox button |
|---|---|---|---|
| 33 | Coin switch, chute 1 | F1 | Coin1 |
| 34 | Coin switch, chute 2 | F2 | Coin2 |
| 35 | Coin switch, chute 3 | F3 | Coin3 |
| 36 | Genre button | Right Alt | MusicGroup, cycles the genre groups |
| 37 | Attract mode button | `'` | AttractMode |
| 38 | Fill queue button | Space, 20 times about 0.125 s apart | Random; tops the queue up with random songs from the current genre |
| 39 | Skip button (optional) | Backspace | Skip |
| 40 | Mute button (optional) | Left Ctrl | Mute |
| 41 | Cancel button (optional) | none | Restarts the 3-digit count, clears the lights and fires the reset solenoid. A half-typed code in Fruitbox clears itself after its `SelectTimeout`. |
| 17 | Selection lights data (through 330 ohm) | | see `SELECTION-LIGHTS.md` |
| 31 | MOSFET gate for reset solenoid (optional) | output | |
| 15, 16 | Volume encoder A, B (only if `USE_ENCODER = true`) | `=` / `-` | VolUp / VolDown |
| 13, 14, 18 to 23, 32 | Spare (13 also lights the Teensy's orange LED) | | |

These keys match `fruitbox/fruitbox.ini` from the Fruitbox configuration thread.

**Fill queue.** Fruitbox has no fill command, but each Random press adds one
random song from the current genre, and it ignores presses once the queue is
full. So the button sends Random `FILL_QUEUE_PRESSES` times, set to 20 to match
`MaxPlayQueueLength = 20` in `fruitbox.ini`. If you raise the queue limit (to 30,
say), change both numbers. A second press while it is still filling is ignored.

**Coin switches.** The coin mechanism has a small switch (often a wire
trip lever) per chute that the coin brushes as it falls. Wire each one directly
to its pin and GND. Then set how many credits each chute gives with
`CreditsPerCoin1`, `CreditsPerCoin2` and `CreditsPerCoin3` in Fruitbox. One thing to
check (my inference, not confirmed for the USC2): if the mechanism has a lockout
coil, it may reject every coin unless that coil is powered. In that case power the
coil from a supply that matches its rating, or block it open mechanically.

## 5. Selection number lights

| LED strip wire | Goes to |
|---|---|
| 5 V | Teensy **VIN** (5 V from USB; fine for the LEDs, never for a pin) |
| GND | Teensy **GND** |
| DIN (data) | 330 ohm resistor, then Teensy pin **17** |

Put a 1000 uF capacitor across 5 V and GND at the strip's input (stripe side to
GND). Details and settings: [`SELECTION-LIGHTS.md`](SELECTION-LIGHTS.md).

## 6. Keyboard reset solenoid (optional)

```
 +24 V DC ──┬───────────── solenoid ─────────┐
            │                                │
            └──── 1N4007 (band to +24 V) ────┤
                                             │
                                        MOSFET drain
 Teensy pin 31 ── 220 Ω ── MOSFET gate       │
                     │                  MOSFET source ── GND (shared with Teensy)
                    10 k
                     │
                    GND
```

1. Measure the coil resistance first. Check that 24 V divided by that resistance
   is well within the MOSFET's and the supply's ratings.
2. The original coil probably ran on AC. Short DC pulses are fine, but don't hold
   it on. The program pulses for 120 ms (`SOLENOID_PULSE_MS`).
3. The IRLZ44N and IRLB8721 switch fully from the Teensy's 3.3 V.
4. Set `USE_RESET_SOLENOID = true` in the program once it is wired.

The program fires the solenoid after the third digit, after a 10 s timeout on a
half-entered selection, when the Cancel button is pressed, and once at power-up.

## 7. Volume

The stock Seeburg volume knob is **not used**. Volume comes from the knob on the
Koolertron macro pad in the glass button bar, which plugs straight into the Pi
and types Fruitbox's `VolUp` (`=`) and `VolDown` (`-`) keys
(`docs/monitor-and-volume.md`). Nothing for volume connects to the
Teensy.

The Teensy still sends an `E:` line over its USB cable for every key, coin and
button; `cabinet-lights/jukebox-bridge.py` on the Pi uses those for the cabinet
lights.

**Encoder (off by default, spare option).** If you would rather have a rotary encoder that
drives Fruitbox's own `VolUp`/`VolDown`, wire A to pin 15, B to pin 16 and the
common to GND, then set `USE_ENCODER = true`. If one click needs two detents,
set `ENC_STEPS_PER_CLICK = 2`. If the direction is backwards, set
`ENC_REVERSE = true`.

## 8. Fruitbox settings that go with this

The Firestar skin's `fruitbox.cfg` already has these, so 3-digit codes from 100
to 243 match the keypad:

```
SelectButtons = 12
SelectButtons = 0123456789
SelectButtons = 0123456789
AutoSelect = Yes
```

The valid codes come from the Pi: each time Fruitbox starts, the launcher
runs `send-song-codes.py`, which reads the skin and sends a line such as
`C100-108,110-118,...,270-278` to the Teensy. The Teensy saves it (EEPROM, so it survives a
power cut) and only sends digits that can make one of those codes. Type `v` in
the Serial Monitor to see the list in use. Until the Pi sends one, the
`SONG_CODES` list near the top of `lights.h` is used (the same 16
blocks). Keep `DIGITS_PER_SELECTION` equal to the number of
`SelectButtons` lines.

Page left and page right also run a light across the selection lamps: right
to left for page left, left to right for page right.

## 9. Bring-up checklist

1. Upload with `SERIAL_DEBUG = true`. Open the Serial Monitor at 115200 baud.
2. Type `1`, `4`, `3` into the Serial Monitor: the selection lights should light
   (nothing is typed on the computer). Type `w` to walk through the LEDs.
3. Press every key and button and check that the right name prints.
4. Drop a coin in each chute and check for exactly one `Coin` line per coin.
   Raise `COIN_DEBOUNCE_MS` if a coin counts twice.
5. Set `SERIAL_DEBUG = false`, upload again, plug into the Pi, and try a full
   3-digit selection in Fruitbox.
