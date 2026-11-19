# Parts and inventory

Every part the jukebox build uses, in one place. Change the **Status** column as
things arrive:

- **Have**: in hand.
- **Ordered**: bought, not arrived.
- **Need**: still to buy.
- **Deciding**: not chosen yet.
- **?**: not recorded yet. Please change it to one of the above.

Each project folder's README has the details (wiring, what to search for).

## Buy now: keypad, coins and lights controller

These are exact items. The Teensy and its screw-terminal board are the whole
controller: no expanders, no jumper wires.

| # | Buy | Qty | Where |
|---|---|---|---|
| 1 | Optional: Seeburg Microlog New Design Keypad Board (part 63-7234). Not needed: the original board tested fine (2026-10-09); only if a key gets unreliable | 1 | [Victory Glass](https://victoryglass.com/product/seeburg-microlog-new-design-keypad-board/) |
| 2 | **Teensy 4.1 with pins** (not the 4.0, not "without pins") | 1 | [PJRC](https://www.pjrc.com/store/teensy41_pins.html), SparkFun, Adafruit or Amazon |
| 3 | Treedix screw-terminal breakout board for Teensy 4.1/3.5/3.6 | 1 | Amazon |
| 4 | Micro-USB to USB-A **data** cable, 1 m | 1 | Any brand that says "data sync" |
| 5 | BTF-LIGHTING WS2812B LED strip, 5V, 144 LEDs/m, 1 m, IP30, black | 1 | Amazon: search exactly that |
| 6 | 330 ohm resistor and 1000 uF 10 V (or higher) capacitor | 1 each | Any electronics kit; for the LED strip |
| 7 | 20-conductor rainbow ribbon cable, 28 AWG, 1 m | 1 | Amazon |
| 8 | Soldering iron kit, temperature adjustable, 60 W | 1 | Amazon. Only if you don't own one. |

Buy later: the keypad backlight 24 V adapter and bulbs (count the sockets first).
The case for the Teensy board is 3D printed.

## Computer, screen and audio

| Part | Qty | Status | Used for | Notes |
|---|---|---|---|---|
| Raspberry Pi 5 | 1 | Have | Runs Fruitbox | |
| 64 GB USB drive | 1 | Have | Pi's system and files, on the blue USB 3 port | |
| 34" ultrawide monitor, flat, IPS | 1 | Deciding | Under the glass | See `docs/monitor-and-volume.md`. Flat, not curved. |
| Second screen for the status display | 1 | ? | Pi's 2nd HDMI port | |
| InnoMaker HiFi DAC HAT (PCM5122) | 1 | ? | Sound out of the Pi | |
| NAD 2-channel amplifier | 1 | ? | Drives the speakers | |

## Keypad, coins and lights controller (`arduino/`)

| Part | Qty | Status | Used for | Notes |
|---|---|---|---|---|
| Original Seeburg keypad and coin mech | 1 each | Have | Inputs | Kept for the stock look. The stock volume knob is not used (volume is the macro pad's knob). |
| Victory Glass 63-7234 keypad contact board | 1 | Optional | Replacement contacts behind the keys | Keeping the original board (every key tested OK 2026-10-09). Buy only if a key gets unreliable. |
| Teensy 4.1 with pins | 1 | Ordered | Turns key presses into keyboard keys, drives the lights | 3.3 V pins |
| Treedix screw-terminal breakout for Teensy 4.1 | 1 | Ordered | A labelled screw terminal for every pin | |
| Micro-USB data cable | 1 | ? | Teensy to Pi | |
| 20-conductor rainbow ribbon cable, 28 AWG | 1 m | ? | Keypad board to the Teensy | |
| Soldering iron, solder and tip cleaner | 1 | Ordered | | |
| Heat-shrink tube or electrical tape | | ? | | |
| Multimeter | 1 | Have | Testing | |
| 3D-printed case for the Teensy board | 1 | Need | Mounting it in the cabinet | Designed in this project |

## Keypad backlight

| Part | Qty | Status | Used for | Notes |
|---|---|---|---|---|
| 24 V DC power adapter | 1 | Need | Powers the keypad bulbs | Original bulbs are marked 28 V |
| BA9S 24 V LED bulbs, non-polarity | 1 per bulb socket | Need | Replace the old bulbs | Count the sockets |

## Selection number lights (`arduino/SELECTION-LIGHTS.md`, `3dPrints/LampPanel/`)

| Part | Qty | Status | Used for | Notes |
|---|---|---|---|---|
| WS2812B LED strip, 5 V, 144 LEDs per metre | 1 m | Need | Lights the 23 selection numbers | Close-spaced numbers need a dense strip |
| ALITOVE WS2811 5 V 12 mm bullet pixels, 50 pack | 1 | Ordered | Alternative to the strip | Only if the numbers are 15 mm or more apart |
| 330 ohm resistor | 1 | Need | In the LED data wire | |
| 1000 uF capacitor, 10 V or more | 1 | Need | Across the LED power at the input | |

## Cabinet lights (`cabinet-lights/`)

| Part | Qty | Status | Used for | Notes |
|---|---|---|---|---|
| 5 V addressable LEDs (WS2812B strip or WS2811 5 V bullets) | to decide | Deciding | Lights around the cabinet | Locations and lengths to be decided |
| 5 V 40 A screw-terminal power supply (110 V in) | 1 | Have | Powers the cabinet lights | Wiring in cabinet-lights/README.md. The Pi drives the strips from pin 32, all four in one chain; no ESP32 |
| Inline blade fuse holder + 5 A fuse | 1 per strip | Need | In each strip's + wire | |
| 330 ohm resistor and 1000 uF 10 V capacitor | 1 resistor, 1 capacitor per strip | Need | Pi data wire, power input of each strip | |

## Glass button bar (`3dPrints/ButtonBar/`)

| Part | Qty | Status | Used for | Notes |
|---|---|---|---|---|
| Koolertron 4-key + knob macro pad (Amazon B0GWZY592K) | 1 | Ordered | Keys: page left, page right, genre, random song. Knob: volume up/down, press to mute | Shell is designed once it arrives |
| 3M VHB tape, clear (4910) | 1 | Need | Sticks the bar to the glass | |
| Right-angle USB-C cable and thin USB-C ribbon | 1 | Need | Pad to Pi, under the glass drawer | |

## Optional

| Part | Qty | Status | Used for | Notes |
|---|---|---|---|---|
| Logic-level MOSFET (IRLZ44N), 1N4007 diode, 220 ohm and 10 k resistors, 24 V supply | 1 set | Deciding | Keypad reset solenoid | Only if the keys latch |
| 74AHCT125 level shifter | 1 | Deciding | LED strip data | Only if the LEDs flicker |

## Not used any more

The Pro Micro and MCP23017 expanders from the earlier plan were replaced by the
Teensy 4.1 on 2026-10-07 (more pins, no expanders).
