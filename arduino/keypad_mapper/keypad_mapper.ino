/*
  Seeburg keypad mapper (test sketch) for Teensy 4.1

  Finds out how the Microlog contact board is wired, whatever the scheme:
  one wire per key, a row/column grid, or keys that close two circuits.

  Wiring: one wire from each edge finger of the keypad board straight to a
  Teensy pin. Finger numbers start at 1:
    fingers 1..13  -> Teensy pins 0..12
    fingers 14..20 -> Teensy pins 24..30
  Nothing else is connected to the keypad board. It needs no power.
  These are the same pins the main program (seeburg_keypad) uses.

  Use: Tools > Board > Teensy 4.1, upload, then open the Serial Monitor at
  115200 baud. Press and hold each key in turn. The sketch prints which
  fingers that key joins together, e.g.
      KEY DOWN: 3-11 7-14
  Copy the whole log into the project thread.

  How it works: each finger in turn is driven LOW while all other1s are pulled
  up; any other finger that reads LOW is connected to it.
*/

const uint8_t KEYPAD_PINS[] = {
   0,  1,  2,  3,  4,  5,  6,  7,  8,  9, 10, 11, 12,   // fingers 1..13
  24, 25, 26, 27, 28, 29, 30                            // fingers 14..20
};
const uint8_t  NUM_FINGERS  = sizeof(KEYPAD_PINS);
const uint16_t SETTLE_SCANS = 3;   // a reading must repeat this many scans in a row

// connected[i] has bit j set when finger i+1 is joined to finger j+1 (j > i).
uint32_t connected[NUM_FINGERS];
uint32_t lastReported[NUM_FINGERS];
uint32_t baseline[NUM_FINGERS];     // pairs that are joined with no key pressed
uint8_t  sameCount = 0;

void scan() {
  for (uint8_t i = 0; i < NUM_FINGERS; i++) {
    connected[i] = 0;
    pinMode(KEYPAD_PINS[i], OUTPUT);
    digitalWriteFast(KEYPAD_PINS[i], LOW);
    delayMicroseconds(10);
    for (uint8_t j = i + 1; j < NUM_FINGERS; j++) {
      if (!digitalReadFast(KEYPAD_PINS[j])) connected[i] |= 1UL << j;
    }
    pinMode(KEYPAD_PINS[i], INPUT_PULLUP);
  }
}

void printPairs(const char *label, const uint32_t *pairs, const uint32_t *exclude) {
  Serial.print(label);
  bool any = false;
  for (uint8_t i = 0; i < NUM_FINGERS; i++) {
    uint32_t p = pairs[i] & ~(exclude ? exclude[i] : 0);
    for (uint8_t j = i + 1; j < NUM_FINGERS; j++) {
      if (p & (1UL << j)) {
        Serial.print(' '); Serial.print(i + 1); Serial.print('-'); Serial.print(j + 1);
        any = true;
      }
    }
  }
  if (!any) Serial.print(" (none)");
  Serial.println();
}

void setup() {
  Serial.begin(115200);
  while (!Serial && millis() < 4000) {}   // wait for the Serial Monitor

  for (uint8_t i = 0; i < NUM_FINGERS; i++) pinMode(KEYPAD_PINS[i], INPUT_PULLUP);
  Serial.println("Seeburg keypad mapper (Teensy 4.1)");
  Serial.println("Don't touch the keypad for 2 seconds...");
  delay(2000);
  scan();
  memcpy(baseline, connected, sizeof(baseline));
  memcpy(lastReported, connected, sizeof(lastReported));
  printPairs("ALWAYS JOINED (no key pressed):", baseline, nullptr);
  Serial.println("Now press and hold each key, one at a time.");
}

void loop() {
  static uint32_t previous[NUM_FINGERS];
  scan();
  if (memcmp(connected, previous, sizeof(connected)) == 0) {
    if (sameCount < SETTLE_SCANS) sameCount++;
  } else {
    sameCount = 0;
    memcpy(previous, connected, sizeof(previous));
  }

  if (sameCount == SETTLE_SCANS && memcmp(connected, lastReported, sizeof(connected)) != 0) {
    bool keyDown = false;
    for (uint8_t i = 0; i < NUM_FINGERS; i++) if (connected[i] & ~baseline[i]) keyDown = true;
    if (keyDown) printPairs("KEY DOWN:", connected, baseline);
    else         Serial.println("released");
    memcpy(lastReported, connected, sizeof(lastReported));
  }
  delay(5);
}
