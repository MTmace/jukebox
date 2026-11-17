/*
  Seeburg USC2 Firestar -> Fruitbox USB keyboard
  Board: Teensy 4.1 (PJRC). In the Arduino IDE (with Teensyduino installed):
         Tools > Board > Teensy 4.1
         Tools > USB Type > "Serial + Keyboard + Mouse + Joystick"
  Library: "Adafruit NeoPixel" (Library Manager).

  What it does
  - Scans the Seeburg Microlog keypad contact board directly: every edge
    finger has its own Teensy pin, no expanders. Each key is defined by the
    finger pairs it joins (KEYS table below, filled in from the
    keypad_mapper test).
  - Types the keys Fruitbox listens for by default, so no button remapping
    is needed in Fruitbox: digits 0..9, F1..F3 for coins, Right Alt for
    genre, ' for attract mode, Left/Right arrows for the two RESET keys
    (Left RESET = page left, Right RESET = page right).
  - Sends an "E:<event>" line over USB serial for every key, coin and button
    ("E:key 4", "E:select 143", "E:reject 358", "E:coin 1", "E:genre", ...). jukebox-bridge.py
    on the Pi (cabinet-lights/) turns these into WLED presets.
  - Volume is not handled here: the knob on the USB macro pad types Fruitbox's
    VolUp (=) / VolDown (-) keys directly. The stock Seeburg knob is not used.
  - Lights the 23 selection numbers (lights.h, see selection-lights/README.md).
  - Screen sleep: when the Pi turns the screens off at night it sends "S"
    (screen-sleep.sh). The next keypad press then only wakes the screens
    (it types Shift, which Fruitbox ignores) and is not used as a digit.
    "A" from the Pi (screens woke some other way) cancels that.
  - Each selection is 3 digits. The valid codes come from the Pi ("C100-108,110-118,...",
    send-song-codes.py, saved on the Teensy), else SONG_CODES in lights.h. Every digit
    is typed as soon as it is pressed; Fruitbox collects the three.
  - Optionally pulses the original keyboard reset solenoid (through a
    MOSFET) after the third digit, in case your keys latch.

  Serial Monitor test (115200 baud): typing 0-9 acts like a keypad press for
  the lights only (nothing is typed on the computer); w = LED walk test,
  i = idle dance, c = clear, v = lights version and codes, l / r = page sweep,
  C100-108,110-118,... = set the valid codes,
  S / A = screens asleep / awake.

  See WIRING.md in this folder for the wiring.
*/

#include <Adafruit_NeoPixel.h>
#include "lights.h"

// ---------------------------------------------------------------- options
const uint8_t  DIGITS_PER_SELECTION = 3;   // must match the skin's SelectButtons lines
const bool     USE_RESET_SOLENOID = false;  // true once the MOSFET + solenoid are wired
const uint16_t SOLENOID_PULSE_MS  = 120;    // keep short: original coil may be AC rated
const uint32_t PENDING_TIMEOUT_MS = 10000;  // drop a half-entered selection after this; keep
                                            // equal to the skin's SelectTimeout (10 s)
const uint8_t  DEBOUNCE_MS        = 15;     // extra buttons
const uint8_t  KEYPAD_SETTLE_MS   = 40;     // a key's two contacts may not close at the same
                                            // instant; wait until the reading is steady
const uint8_t  KEYPAD_SINGLE_MS   = 150;    // 0 and 3 join one pair, which is also the first
                                            // contact of 4..7 closing on a slow press, so they
                                            // type after this long held, or on release
const uint8_t  COIN_DEBOUNCE_MS   = 4;      // coin wire trips give short pulses
const uint16_t KEY_TAP_MS         = 25;     // how long each key is held down
// Fill queue button: taps Random (Space) this many times, which tops the play
// queue up with random songs from the current genre. Fruitbox ignores the
// extra presses once the queue is full. Keep equal to MaxPlayQueueLength in
// fruitbox.ini (20 there now).
const uint8_t  FILL_QUEUE_PRESSES = 20;
const uint16_t FILL_QUEUE_GAP_MS  = 125;    // time between Random presses
const bool     SERIAL_DEBUG       = false;  // also print events on the USB serial port
                                            // (jukebox-bridge.py ignores lines without "V:" or "E:")

// ------------------------------------------------------------------- pins
const uint8_t PIN_SOLENOID = 31;            // MOSFET gate for keyboard reset solenoid

// --------------------------------------------------------- keypad mapping
// Keypad board finger 1 goes to KEYPAD_PINS[0], finger 2 to KEYPAD_PINS[1],
// and so on. Up to 20 fingers.
const uint8_t KEYPAD_PINS[] = {
   0,  1,  2,  3,  4,  5,  6,  7,  8,  9, 10, 11, 12,   // fingers 1..13
  24, 25, 26, 27, 28, 29, 30                            // fingers 14..20
};
const uint8_t NUM_FINGERS = sizeof(KEYPAD_PINS);

// Each key joins one or two pairs of wires when pressed. Measured
// with keypad_mapper (2026-10-29) through the original harness: its 13 loose
// wires, labelled 1..13, on Teensy pins 0..12 (so wire n = "finger" n here),
// plus Left RESET's own wire on pin 24 (finger 14).
// Some keys share a pair (3 = 4-10 is also part of 4, 5 and 6), so when
// several keys match, the one with more matching pairs wins.
// NONE in a1 = key not mapped; NONE in a2 = the key joins only one pair.
const uint8_t NONE = 0;
struct KeyDef { uint16_t key; uint8_t a1, b1, a2, b2; const char *name; };
uint16_t selectCode = 0;      // digits typed so far, for the "E:select" event
KeyDef KEYS[] = {
  { '0',   8, 10, NONE, NONE, "0" },
  { '1',   3, 10,    3, 13, "1" },
  { '2',   9, 10,    9, 13, "2" },
  { '3',   4, 10, NONE, NONE, "3" },
  { '4',   4,  8,    8, 10, "4" },
  { '5',   4,  9,    9, 10, "5" },
  { '6',   3,  4,    4, 10, "6" },
  { '7',   3,  8,    8, 10, "7" },
  { '8',   3,  5,    5,  9, "8" },
  { '9',   5,  8,    8,  9, "9" },
  // Left and Right RESET used to share 1-7 2-7. The shared wire 7 track between them
  // was cut and Left RESET's side was wired to pin 24 (2026-10-29).
  { KEY_LEFT,  1, 14,    2, 14, "Left RESET: page left" },
  { KEY_RIGHT, 1,  7,    2,  7, "Right RESET: page right" },
};
const uint8_t NUM_KEYS = sizeof(KEYS) / sizeof(KEYS[0]);

// ------------------------------------------------ other inputs (Teensy pins)
// Each switch goes between its pin and GND. Keys are Fruitbox v3 defaults.
struct DirectInput { uint8_t pin; uint16_t key; uint8_t debounce; const char *name; const char *event; };

// Values in the key field that trigger an action instead of a key.
const uint16_t ACTION_CANCEL     = 0;
const uint16_t ACTION_FILL_QUEUE = 0xFFFF;  // not a real key code

const DirectInput DIRECT[] = {
  {33, KEY_F1,            COIN_DEBOUNCE_MS, "Coin1 (F1)", "coin 1" },     // first coin chute switch
  {34, KEY_F2,            COIN_DEBOUNCE_MS, "Coin2 (F2)", "coin 2" },     // second coin chute switch
  {35, KEY_F3,            COIN_DEBOUNCE_MS, "Coin3 (F3)", "coin 3" },     // third coin chute switch
  {36, KEY_RIGHT_ALT,     DEBOUNCE_MS,      "Genre / MusicGroup (Right Alt)", "genre" },
  {37, '\'',              DEBOUNCE_MS,      "AttractMode (')", "attract" },
  {38, ACTION_FILL_QUEUE, DEBOUNCE_MS,      "Fill queue (Space x FILL_QUEUE_PRESSES)", "fill" },
  {39, KEY_BACKSPACE,     DEBOUNCE_MS,      "Skip (Backspace)", "skip" },
  {40, KEY_LEFT_CTRL,     DEBOUNCE_MS,      "Mute (Left Ctrl)", "mute" },
  {41, ACTION_CANCEL,     DEBOUNCE_MS,      "Cancel", "cancel" },         // clears a half-entered selection
};
const uint8_t NUM_DIRECT = sizeof(DIRECT) / sizeof(DIRECT[0]);

// Optional volume encoder (EC11 style). Clockwise taps VolUp (=),
// anticlockwise taps VolDown (-). Off by default: the macro pad's knob is
// the volume control now.
const bool    USE_ENCODER         = false;
const uint8_t PIN_ENC_A           = 15;
const uint8_t PIN_ENC_B           = 16;
const int8_t  ENC_STEPS_PER_CLICK = 4;    // most EC11 encoders; try 2 if it needs two clicks
const bool    ENC_REVERSE         = false; // flip if volume goes the wrong way
// Free for later: 13 (also the orange LED), 14, 18..23, 32.

// ------------------------------------------------------------------ state
struct Debounced {
  bool     stable;      // true = pressed
  bool     raw;
  uint32_t changedAt;
};

// One press types one key, even when its contacts close one at a time.
int8_t    pressKey   = -1;      // key the contacts currently match (-1 = none)
uint32_t  pressSince = 0;       // when that reading started
int8_t    pressReady = -1;      // a one-pair key that has settled, typed on release
bool      pressTyped = false;   // this press has typed; wait for release
Debounced directState[sizeof(DIRECT) / sizeof(DIRECT[0])];
uint32_t  joined[20];   // joined[i] bit j: finger i+1 is connected to finger j+1

uint8_t  digitsEntered = 0;   // digits typed so far in this selection
uint32_t pendingSince  = 0;
bool     screensAsleep = false;   // set by "S" from the Pi, see screen-sleep.sh
uint32_t solenoidOffAt = 0;
uint8_t  fillRemaining = 0;   // Random presses still to send for Fill queue
uint32_t fillNextAt    = 0;

volatile int8_t  encSteps = 0;
volatile uint8_t encLast  = 0;

// Quadrature decoder: index = previous AB << 2 | current AB.
void encoderIsr() {
  static const int8_t table[16] = { 0, -1, 1, 0, 1, 0, 0, -1, -1, 0, 0, 1, 0, 1, -1, 0 };
  uint8_t ab = (digitalReadFast(PIN_ENC_A) << 1) | digitalReadFast(PIN_ENC_B);
  encSteps += table[(encLast << 2) | ab];
  encLast = ab;
}

// ---------------------------------------------------------------- helpers
void debug(const char *what, const char *detail) {
  if (!SERIAL_DEBUG) return;
  Serial.print(millis());
  Serial.print("  ");
  Serial.print(what);
  Serial.print(" ");
  Serial.println(detail);
}

// One line per event for jukebox-bridge.py on the Pi, e.g. "E:coin 1".
void event(const char *what, int n = -1) {
  Serial.print("E:");
  Serial.print(what);
  if (n >= 0) { Serial.print(' '); Serial.print(n); }
  Serial.println();
}

void tapKey(uint16_t key) {
  Keyboard.press(key);
  delay(KEY_TAP_MS);
  Keyboard.release(key);
  delay(KEY_TAP_MS);
}

void pulseSolenoid() {
  if (!USE_RESET_SOLENOID) return;
  digitalWrite(PIN_SOLENOID, HIGH);
  solenoidOffAt = millis() + SOLENOID_PULSE_MS;
  debug("solenoid", "pulse");
}

void clearPending(bool releaseButtons) {
  digitsEntered = 0;
  if (releaseButtons) pulseSolenoid();
}

// Returns true on a debounced press (not on release).
bool updateDebounce(Debounced &d, bool rawPressed, uint8_t debounceMs, uint32_t now) {
  if (rawPressed != d.raw) {
    d.raw = rawPressed;
    d.changedAt = now;
  }
  if (d.raw != d.stable && (uint32_t)(now - d.changedAt) >= debounceMs) {
    d.stable = d.raw;
    return d.stable;
  }
  return false;
}

// Drive each finger LOW in turn; any other finger that reads LOW is joined to it.
void scanKeypad() {
  for (uint8_t i = 0; i < NUM_FINGERS; i++) {
    joined[i] = 0;
    pinMode(KEYPAD_PINS[i], OUTPUT);
    digitalWriteFast(KEYPAD_PINS[i], LOW);
    delayMicroseconds(10);
    for (uint8_t j = i + 1; j < NUM_FINGERS; j++) {
      if (!digitalReadFast(KEYPAD_PINS[j])) joined[i] |= 1UL << j;
    }
    pinMode(KEYPAD_PINS[i], INPUT_PULLUP);
  }
}

// Fingers are numbered from 1, as on the keypad board.
bool isJoined(uint8_t a, uint8_t b) {
  if (a == NONE || b == NONE || a == b || a > NUM_FINGERS || b > NUM_FINGERS) return false;
  if (a > b) { uint8_t t = a; a = b; b = t; }
  return joined[a - 1] & (1UL << (b - 1));
}

bool keyPressed(const KeyDef &k) {
  if (k.a1 == NONE) return false;
  return isJoined(k.a1, k.b1) && (k.a2 == NONE || isJoined(k.a2, k.b2));
}

// The one key that is down: of the keys whose pairs are all joined, the one
// with the most pairs (pressing 6 also joins 7-10, which alone means 5).
int8_t keyDown() {
  int8_t best = -1;
  uint8_t bestPairs = 0;
  for (uint8_t i = 0; i < NUM_KEYS; i++) {
    if (!keyPressed(KEYS[i])) continue;
    uint8_t pairs = KEYS[i].a2 == NONE ? 1 : 2;
    if (pairs > bestPairs) { best = i; bestPairs = pairs; }
  }
  return best;
}

void onDigit(uint8_t d, bool typeIt) {
  char s[2] = { (char)('0' + d), 0 };
  debug("digit", s);
  lightsKey(d, digitsEntered);   // the lamps blink a digit that has no lamp in its place
  event("key", d);
  // A digit that can't lead to a song in this place (hundreds 1-2, tens 0-7,
  // and only codes in SONG_CODES) is not sent; the next press can correct it.
  if (!lights::fits(digitsEntered ? selectCode : 0, digitsEntered, d)) { event("ignored", d); return; }
  if (digitsEntered == 0) selectCode = 0;
  selectCode = selectCode * 10 + d;
  pendingSince = millis();       // only digits Fruitbox sees restart the timeout, like its own
  if (typeIt) tapKey('0' + d);   // each good digit goes to Fruitbox as soon as it's pressed
  if (++digitsEntered >= DIGITS_PER_SELECTION) {
    event("select", selectCode);
    clearPending(true);
  }
}

void typeKey(uint8_t i) {
  uint16_t k = KEYS[i].key;
  if (screensAsleep) {
    // This press only wakes the screens; any key wakes them, and Shift
    // alone does nothing in Fruitbox.
    screensAsleep = false;
    debug("screens", "wake");
    event("wake");
    tapKey(MODIFIERKEY_SHIFT);
    return;
  }
  if (k >= '0' && k <= '9') onDigit(k - '0', true);
  else {
    debug("button", KEYS[i].name);
    event(k == KEY_LEFT ? "page left" : "page right");
    lightsPage(k == KEY_LEFT ? -1 : 1);
    tapKey(k);
  }
}

// ------------------------------------------------------------------ setup
void setup() {
  pinMode(PIN_SOLENOID, OUTPUT);
  digitalWrite(PIN_SOLENOID, LOW);

  for (uint8_t i = 0; i < NUM_FINGERS; i++) pinMode(KEYPAD_PINS[i], INPUT_PULLUP);
  for (uint8_t i = 0; i < NUM_DIRECT; i++) pinMode(DIRECT[i].pin, INPUT_PULLUP);

  if (USE_ENCODER) {
    pinMode(PIN_ENC_A, INPUT_PULLUP);
    pinMode(PIN_ENC_B, INPUT_PULLUP);
    encLast = (digitalReadFast(PIN_ENC_A) << 1) | digitalReadFast(PIN_ENC_B);
    attachInterrupt(digitalPinToInterrupt(PIN_ENC_A), encoderIsr, CHANGE);
    attachInterrupt(digitalPinToInterrupt(PIN_ENC_B), encoderIsr, CHANGE);
  }

  Serial.begin(115200);     // event lines for jukebox-bridge.py (and debug output)
  lightsBegin();

  for (uint8_t i = 0; i < NUM_KEYS; i++) {
    if (KEYS[i].a1 == NONE) { debug("keypad", "KEYS table not filled in yet"); break; }
  }

  delay(500);   // let the Pi enumerate the keyboard
  pulseSolenoid();   // a key that is already latched at power-up is released
}

// ------------------------------------------------------------------- loop
void loop() {
  uint32_t now = millis();

  scanKeypad();
  int8_t down = keyDown();
  if (down != pressKey) { pressKey = down; pressSince = now; }
  uint32_t held = now - pressSince;
  if (down < 0) {
    if (held >= KEYPAD_SETTLE_MS) {           // released
      if (!pressTyped && pressReady >= 0) typeKey(pressReady);
      pressTyped = false;
      pressReady = -1;
    }
  } else if (!pressTyped && held >= KEYPAD_SETTLE_MS) {
    if (KEYS[down].a2 == NONE && held < KEYPAD_SINGLE_MS) pressReady = down;  // may still become 4..7
    else { typeKey(down); pressTyped = true; pressReady = -1; }
  }

  for (uint8_t i = 0; i < NUM_DIRECT; i++) {
    bool pressed = digitalReadFast(DIRECT[i].pin) == LOW;
    if (updateDebounce(directState[i], pressed, DIRECT[i].debounce, now)) {
      debug("button", DIRECT[i].name);
      event(DIRECT[i].event);
      if (DIRECT[i].key == ACTION_FILL_QUEUE) {
        if (!fillRemaining) { fillRemaining = FILL_QUEUE_PRESSES; fillNextAt = now; }
      }
      else if (DIRECT[i].key) tapKey(DIRECT[i].key);
      else { clearPending(true); lightsClear(); }   // Cancel
    }
  }

  // From the Pi: S / A = screens asleep / awake. The rest are Serial
  // Monitor test commands.
  while (Serial.available()) {
    char c = Serial.read();
    if (c == 'S')      { screensAsleep = true;  debug("screens", "asleep"); }
    else if (c == 'A') { screensAsleep = false; debug("screens", "awake"); }
    else if (c == 'C') {               // the skin's codes from send-song-codes.py
      String list = Serial.readStringUntil('\n');
      if (lights::setCodes(list.c_str())) lights::printCodes();
      else Serial.println("V:codes rejected");
    }
    else if (c >= '0' && c <= '9') onDigit(c - '0', false);
    else lightsCommand(c);
  }

  if (USE_ENCODER) {
    noInterrupts();
    int8_t steps = encSteps;
    if (steps >= ENC_STEPS_PER_CLICK)       encSteps -= ENC_STEPS_PER_CLICK;
    else if (steps <= -ENC_STEPS_PER_CLICK) encSteps += ENC_STEPS_PER_CLICK;
    interrupts();
    bool up   = ENC_REVERSE ? (steps <= -ENC_STEPS_PER_CLICK) : (steps >= ENC_STEPS_PER_CLICK);
    bool down = ENC_REVERSE ? (steps >= ENC_STEPS_PER_CLICK) : (steps <= -ENC_STEPS_PER_CLICK);
    if (up)   { debug("volume", "up");   tapKey('='); }
    if (down) { debug("volume", "down"); tapKey('-'); }
  }

  // Fill queue: one Random press per gap, so the rest of the loop keeps running.
  if (fillRemaining && (int32_t)(millis() - fillNextAt) >= 0) {
    tapKey(' ');
    fillRemaining--;
    fillNextAt = millis() + FILL_QUEUE_GAP_MS;
  }

  // millis(), not now: a digit typed earlier in this loop set pendingSince after now
  if (digitsEntered && (uint32_t)(millis() - pendingSince) > PENDING_TIMEOUT_MS) {
    debug("timeout", "half selection dropped");
    clearPending(true);
  }

  if (solenoidOffAt && (int32_t)(millis() - solenoidOffAt) >= 0) {
    digitalWrite(PIN_SOLENOID, LOW);
    solenoidOffAt = 0;
  }

  lightsUpdate();
  delay(1);
}
