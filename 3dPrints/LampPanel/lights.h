// Selection number lights: a 5 V addressable LED strip (WS2812B) behind the
// 20 selection numbers (1 2, then 0-7, then 0-9). Included by seeburg_keypad.ino; see
// selection-lights/README.md for the parts, wiring and settings.
//
// LIGHTS VERSION 10 (2026-10-28): the tens row is 0-7 like the real Firestar
// (selections 100-179 and 200-279), so the panel has 20 numbers, not 22.
// LIGHTS VERSION 9 (2026-10-14): when keys are pressed quickly, each digit's slide
// waits for the one before it to land, so they always arrive in order.
// LIGHTS VERSION 8 (2026-10-12): idle twinkle lights a few numbers together
// (TWINKLE_GROUP at a time) and holds them fully lit for TWINKLE_HOLD_MS.
// LIGHTS VERSION 7 (2026-10-10): each key's light starts at the ones end and slides
// across the ones, tens and hundreds to its number (100 ms per number), 10 s hold,
// entries fade out together, slow fading idle twinkle, panel order 1 2 / 0-9 / 0-9.
// Type v in the Serial Monitor to print the version on the Teensy.
#pragma once

namespace lights {

const char VERSION[] = "Lights version 10 (2026-10-28)";

// ---------- settings you may change ----------
const uint8_t  LED_PIN          = 17;    // data wire of the LED strip (Teensy pin 17)
const uint8_t  NUM_LEDS         = 20;    // numbers on the panel
const uint8_t  STRIP_LEDS       = 20;    // LEDs on the string or strip (more is fine: extras stay off)
const uint16_t COLOR_ORDER      = NEO_GRB; // WS2812B strips are GRB; try NEO_RGB if red and green swap
const uint8_t  FIRST_ROW_LEN    = 2;
const uint8_t  FIRST_ROW[FIRST_ROW_LEN] = { 1, 2 };   // numbers printed in row 0, left to right
const uint8_t  TENS_ROW_LEN     = 8;
const uint8_t  TENS_ROW[TENS_ROW_LEN] = { 0, 1, 2, 3, 4, 5, 6, 7 };   // row 1 (tens), left to right
const uint8_t  ONES_ROW[10]     = { 0, 1, 2, 3, 4, 5, 6, 7, 8, 9 };   // row 2 (ones), left to right
const uint16_t LOWEST_CODE      = 100;   // skin codes; anything else blinks and clears
const uint16_t HIGHEST_CODE     = 263;   // 144 songs: 100-179, then 200-263

const uint8_t  SELECT_BRIGHT    = 120;   // 0-255, numbers while selecting
const uint8_t  IDLE_BRIGHT      = 60;    // 0-255, idle twinkle (kept low for USB power)
const uint8_t  LIT_R = 255, LIT_G = 120, LIT_B = 30;   // warm white; ignored by single-colour LEDs

const uint16_t SWEEP_STEP_MS    = 100;   // time per number as the light slides in
const uint8_t  RUN_IN_FROM      = NUM_LEDS - 1;  // where every key's light starts: 19 = the "9" of the ones
                                         // (far right). 10 = the "0" of the ones.
const uint16_t HOLD_MS          = 10000; // numbers stay on after the 3rd digit
const uint16_t FADE_MS          = 2000;  // then fade out together over this long
const uint16_t ENTRY_TIMEOUT_MS = 15000; // half-typed code fades out after this
const uint32_t IDLE_AFTER_MS    = 60000; // no key for this long starts the dance
const uint16_t TWINKLE_EVERY_MS = 1500;  // idle: a new group starts to twinkle this often
const uint8_t  TWINKLE_GROUP    = 3;     // idle: how many numbers light up together
const uint16_t TWINKLE_HOLD_MS  = 1500;  // idle: time a number stays fully lit
const uint16_t TWINKLE_IN_MS    = 1500;  // idle: time for a number to fade up
const uint16_t TWINKLE_OUT_MS   = 2500;  // idle: time for it to fade back out

// Which LED in the string sits behind each number.
// Order here: row 0 left to right, then row 1 left to right, then row 2.
// Use the "w" walk test to check, then edit if your string runs differently.
// With a close-spaced strip, put the number of the LED nearest each number;
// LEDs not listed stay off.
const uint8_t LED_INDEX[NUM_LEDS] = {
   0,  1,
   2,  3,  4,  5,  6,  7,  8,  9,
  10, 11, 12, 13, 14, 15, 16, 17, 18, 19
};
// ---------------------------------------------

const uint8_t ROW_START[3] = { 0, FIRST_ROW_LEN, FIRST_ROW_LEN + TENS_ROW_LEN };
const uint8_t ROW_LEN[3]   = { FIRST_ROW_LEN, TENS_ROW_LEN, 10 };

Adafruit_NeoPixel strip(STRIP_LEDS, LED_PIN, COLOR_ORDER + NEO_KHZ800);

enum State { BLANK, ENTERING, HOLDING, FADING, REJECTING, DANCING, WALKING };
State state = BLANK;

int8_t   pos[3];            // position in each row of the entered digit, -1 = none
uint32_t sweepStart[3];
uint8_t  count = 0;         // digits entered so far
uint32_t stateStart = 0;
uint32_t lastKey = 0;
uint8_t  level[NUM_LEDS];   // brightness of each panel position, 0-255
int8_t   walkShown = -1;

void enter(State s) { state = s; stateStart = millis(); }

void clearEntry() {
  count = 0;
  for (uint8_t r = 0; r < 3; r++) pos[r] = -1;
}

// Position of a digit within its row, or -1 if that row has no such number.
int8_t positionOf(uint8_t row, uint8_t digit) {
  const uint8_t *nums = row == 0 ? FIRST_ROW : row == 1 ? TENS_ROW : ONES_ROW;
  for (uint8_t i = 0; i < ROW_LEN[row]; i++) if (nums[i] == digit) return i;
  return -1;
}

// The number printed at a position in a row.
uint8_t digitAt(uint8_t row, uint8_t p) { return row == 0 ? FIRST_ROW[p] : row == 1 ? TENS_ROW[p] : ONES_ROW[p]; }

uint16_t enteredCode() { return digitAt(0, pos[0]) * 100 + digitAt(1, pos[1]) * 10 + digitAt(2, pos[2]); }

uint16_t sweepTime(uint8_t row);

void key(uint8_t digit) {
  lastKey = millis();
  if (state != ENTERING || count == 3) clearEntry();   // a new selection wipes the old one
  int8_t p = positionOf(count, digit);
  if (p < 0) { enter(REJECTING); return; }      // e.g. a 9 as the first digit, or an 8 or 9 as the second
  pos[count] = p;
  // Start this digit's slide once the previous one has landed (or now, if it has).
  uint32_t start = millis();
  if (count > 0) {
    uint32_t prevEnd = sweepStart[count - 1] + sweepTime(count - 1);
    if ((int32_t)(prevEnd - start) > 0) start = prevEnd;
  }
  sweepStart[count] = start;
  count++;
  enter(ENTERING);
  if (count == 3) {
    uint16_t code = enteredCode();
    Serial.print(F("Code ")); Serial.println(code);
    // HOLDING starts once the third sweep has finished (see update()).
    if (code < LOWEST_CODE || code > HIGHEST_CODE) Serial.println(F("  not a song: will blink"));
  }
}

// Panel position (0-19) of the entered digit in a row.
uint8_t target(uint8_t row) { return ROW_START[row] + pos[row]; }

uint16_t sweepTime(uint8_t row) {
  uint8_t g = target(row);
  return (g > RUN_IN_FROM ? g - RUN_IN_FROM : RUN_IN_FROM - g) * SWEEP_STEP_MS;
}

// Draw the entered digits. Each light starts at RUN_IN_FROM (the far right "9"
// of the ones) and slides across the whole panel until it stops on its number,
// so a hundreds digit crosses the ones and tens on the way.
void drawEntry(uint8_t scale) {
  uint32_t now = millis();
  for (uint8_t r = 0; r < count; r++) {
    if ((int32_t)(now - sweepStart[r]) < 0) continue;   // waiting for the digit before it
    uint8_t g = target(r);
    int8_t dir = g < RUN_IN_FROM ? -1 : 1;
    uint8_t dist = g < RUN_IN_FROM ? RUN_IN_FROM - g : g - RUN_IN_FROM;
    uint32_t steps = (now - sweepStart[r]) / SWEEP_STEP_MS;
    uint8_t at = steps >= dist ? g : RUN_IN_FROM + dir * (int16_t)steps;
    if (level[at] < scale) level[at] = scale;
    if (at != g && at != RUN_IN_FROM) {                  // short tail while it moves
      uint8_t behind = at - dir;
      if (level[behind] < scale / 4) level[behind] = scale / 4;
    }
  }
}

// Idle: numbers twinkle slowly, each one fading up and then back out.
void drawDance(uint32_t t) {
  static uint32_t started[NUM_LEDS];   // when each number's twinkle began, 0 = dark
  static uint32_t lastSpawn = 0;
  uint32_t now = millis();
  if (t < 15) { memset(started, 0, sizeof(started)); lastSpawn = now; }   // idle just began

  if (now - lastSpawn >= TWINKLE_EVERY_MS) {
    lastSpawn = now;
    for (uint8_t n = 0; n < TWINKLE_GROUP; n++) {
      uint8_t i = random(NUM_LEDS);
      if (started[i] == 0) started[i] = now;
    }
  }

  for (uint8_t i = 0; i < NUM_LEDS; i++) {
    if (started[i] == 0) continue;
    uint32_t age = now - started[i];
    uint32_t x;   // 0-255
    if (age < TWINKLE_IN_MS) x = 255 * age / TWINKLE_IN_MS;
    else if (age < TWINKLE_IN_MS + TWINKLE_HOLD_MS) x = 255;
    else if (age < TWINKLE_IN_MS + TWINKLE_HOLD_MS + TWINKLE_OUT_MS)
      x = 255 - 255 * (age - TWINKLE_IN_MS - TWINKLE_HOLD_MS) / TWINKLE_OUT_MS;
    else { started[i] = 0; continue; }
    level[i] = x * x / 255;   // squared so the fade looks even to the eye
  }
}

void show(uint8_t brightness) {
  for (uint8_t i = 0; i < NUM_LEDS; i++) {
    uint16_t v = (uint16_t)level[i] * brightness / 255;
    strip.setPixelColor(LED_INDEX[i], strip.Color(LIT_R * v / 255, LIT_G * v / 255, LIT_B * v / 255));
  }
  strip.show();
}

void update() {
  static uint32_t lastShow = 0;
  if (millis() - lastShow < 15) return;   // about 60 frames a second
  lastShow = millis();
  uint32_t now = millis();
  uint32_t t = now - stateStart;
  memset(level, 0, sizeof(level));
  uint8_t bright = SELECT_BRIGHT;

  switch (state) {
    case BLANK:
      if (now - lastKey >= IDLE_AFTER_MS) enter(DANCING);
      break;

    case ENTERING:
      drawEntry(255);
      if (count == 3 && (int32_t)(now - sweepStart[2]) >= (int32_t)sweepTime(2)) {
        uint16_t code = enteredCode();
        enter(code >= LOWEST_CODE && code <= HIGHEST_CODE ? HOLDING : REJECTING);
      } else if (now - lastKey >= ENTRY_TIMEOUT_MS) {
        enter(FADING);   // half-typed code: fade out together like a full one
      }
      break;

    case HOLDING:
      drawEntry(255);
      if (t >= HOLD_MS) enter(FADING);
      break;

    case FADING:
      if (t >= FADE_MS) { clearEntry(); enter(BLANK); break; }
      drawEntry(255 - (uint32_t)255 * t / FADE_MS);
      break;

    case REJECTING:   // blink what was typed 3 times, then clear
      if (t >= 1200) { clearEntry(); enter(BLANK); break; }
      if ((t / 200) % 2 == 0) {
        if (count == 0) for (uint8_t i = 0; i < ROW_LEN[0]; i++) level[i] = 255;   // bad first digit
        else drawEntry(255);
      }
      break;

    case DANCING:
      drawDance(t);
      bright = IDLE_BRIGHT;
      break;

    case WALKING: {   // one LED at a time in string order (ignores LED_INDEX)
      uint8_t n = t / 600;
      if (n >= STRIP_LEDS) { strip.clear(); strip.show(); enter(BLANK); return; }
      if (n != walkShown) { walkShown = n; Serial.print(F("Walk: LED ")); Serial.println(n); }
      strip.clear();
      strip.setPixelColor(n, strip.Color(LIT_R * SELECT_BRIGHT / 255, LIT_G * SELECT_BRIGHT / 255, LIT_B * SELECT_BRIGHT / 255));
      strip.show();
      return;
    }
  }
  show(bright);
}


}  // namespace lights

inline void lightsBegin() {
  lights::strip.begin();
  lights::strip.clear();
  lights::strip.show();
  lights::clearEntry();
  lights::lastKey = millis();
  randomSeed(analogRead(A1));
}

inline void lightsKey(uint8_t digit) { lights::key(digit); }
inline void lightsUpdate()           { lights::update(); }
inline void lightsClear() {
  lights::clearEntry();
  lights::lastKey = millis();
  lights::enter(lights::BLANK);
}

// Serial Monitor test commands: w = walk test, i = idle twinkle, c = clear, v = version.
inline void lightsCommand(char c) {
  if (c == 'w') { lights::clearEntry(); lights::walkShown = -1; lights::enter(lights::WALKING); }
  else if (c == 'i') { lights::clearEntry(); lights::enter(lights::DANCING); }
  else if (c == 'c') lightsClear();
  else if (c == 'v') Serial.println(lights::VERSION);
}
