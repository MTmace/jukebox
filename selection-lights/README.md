# Selection number lights

The top left of the cabinet has 23 lit numbers that show the selection being
typed: one row for the first digit (0 to 2, or 1 to 3 on some panels), then 0 to 9
for the second digit and 0 to 9 for the third. The original lamp string is gone,
so these are lit by a new **addressable LED strip** driven by the same Teensy 4.1
that reads the keypad. The code is `arduino/seeburg_keypad/lights.h`, part of the
main keypad program.

All parts for the whole jukebox are tracked in [`PARTS.md`](../PARTS.md).

Status: planning. The code compiles for the Teensy 4.1 but has not run on real
LEDs yet. Waiting on a photo of the panel's back.

## What it does

| When | The numbers |
|---|---|
| You press a digit | A light runs along that digit's row from the right end, one number at a time, and stops on the number you pressed. |
| After the 3rd digit | All three stay lit for 4 seconds, then fade out over 1.5 seconds. |
| A new selection while they're showing | They clear and show only the new digits. |
| A code that isn't a song (tens digit 8 or 9, or ones digit 9) | What you typed blinks 3 times, then clears. |
| Half a code, then nothing for 10 seconds | Clears. |
| Page left / page right | A light runs across the whole panel, right to left for page left, left to right for page right. |
| No key pressed for 60 seconds | The numbers "dance": a chase, then twinkles, then lights bouncing along each row, changing every 15 seconds. |

**Limit:** Fruitbox can't tell the Teensy that it accepted a song, so any code
on the skin (tens 0-7, ones 0-8) counts as accepted. Idle means "no key for 60 seconds", not "no
song playing". A later upgrade could use Fruitbox's status output on the Pi to
send the real state over the USB cable.

## Parts

| Qty | Part | Notes |
|---|---|---|
| 1 | 5 V addressable LEDs for 23 numbers | The numbers on the panel are very close together, so the best fit is a **WS2812B strip, 144 LEDs per metre, 5 V** (an LED every 7 mm). Cut a piece for each row, stick it behind the numbers, and join the pieces with 3 short wires. The LED nearest each number is used and the rest stay off (`STRIP_LEDS` and `LED_INDEX` in `lights.h`). |
| | Also considered | ALITOVE WS2811 5V 12mm bullet pixels, 50 pack (Amazon). Fine if the numbers are 15 mm or more apart; for closer numbers every wire between bullets would need cutting and rejoining. |
| 1 | 330 ohm resistor | In the data wire, near the first LED. |
| 1 | 1000 uF capacitor, 10 V or more | Across 5 V and ground at the string's input. The stripe side goes to ground. |

## Wiring

Every LED strip has arrows and a "DIN" (data in) marking. Connect the input end:

| LED strip wire | Goes to |
|---|---|
| 5 V (often red) | Teensy **VIN** terminal (5 V from USB; fine for the LEDs) |
| GND (often white or black) | Teensy **GND** terminal |
| DIN / data (often green) | 330 ohm resistor, then Teensy terminal **17** |

Solder the resistor and the capacitor at the strip's end of the cable and cover
them with heat-shrink, so nothing loose sits at the Teensy.

The pieces for each row must run in the direction of the arrows printed on the
strip: the output end of one piece joins the input end of the next (5 V to 5 V,
GND to GND, DO to DI).

Only a few numbers are lit at once, and the brightness is capped in the code, so
the USB power is enough.

The Teensy's data signal is 3.3 V. WS2812B strips almost always accept it. If the
LEDs flicker or show random colours, add a 74AHCT125 level shifter in the data
wire.

## Try it without the keypad

1. Upload `arduino/seeburg_keypad/seeburg_keypad.ino` to the Teensy (see
   `arduino/KEYPAD-BEGINNER-GUIDE.md` for installing the software).
2. Open **Tools → Serial Monitor** and set it to **115200 baud**.
3. Type one of these into the box at the top and press Enter. Nothing is typed on
   your computer; only the lights react.

| Type | What happens |
|---|---|
| `w` | Walk test: lights each LED in strip order, one at a time, and prints its number. Use it to check which LED is behind which number. |
| `1`, then `4`, then `3` | Acts like pressing keys 1, 4, 3. |
| `i` | Starts the idle dance now. |
| `c` | Clears everything. |

## Settings

All at the top of `arduino/seeburg_keypad/lights.h`:

- `FIRST_ROW`: the numbers printed in the first-digit row, left to right. Change
  to `{ 1, 2, 3 }` if your panel shows 1 to 3.
- `STRIP_LEDS`: how many LEDs are on the string or strip in total.
- `LED_INDEX`: which LED in the string sits behind each number. If the walk test
  shows the string running in a different order (for example, snaking back along
  the second row), change this list.
- `SELECT_BRIGHT`, `IDLE_BRIGHT`: brightness from 0 to 255.
- `HOLD_MS`, `FADE_MS`, `SWEEP_STEP_MS`, `IDLE_AFTER_MS`: timings in milliseconds.
- `LIT_R`, `LIT_G`, `LIT_B`: colour, for colour LEDs.
- `COLOR_ORDER`: if red shows as green (or the other way round), change
  `NEO_GRB` to `NEO_RGB`.
