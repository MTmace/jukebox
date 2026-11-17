// Volume knob for the jukebox: reads a pot on A0 and sends "V:<0-1023>" over USB serial.
// Merge into the keypad/coin sketch: call volumeSetup() in setup() and volumeLoop() in loop().
// Serial and Keyboard work together on the Pro Micro (ATmega32U4).

const int VOL_PIN = A0;
const int VOL_DEADBAND = 6;   // ignore jitter smaller than this (out of 1023)
int volSmoothed = 0;
int volSent = -100;
unsigned long volLastSend = 0;

void volumeSetup() {
  Serial.begin(115200);
  volSmoothed = analogRead(VOL_PIN);
}

void volumeLoop() {
  // simple low-pass filter to hide a scratchy old pot
  volSmoothed = (volSmoothed * 7 + analogRead(VOL_PIN)) / 8;
  unsigned long now = millis();
  bool moved = abs(volSmoothed - volSent) >= VOL_DEADBAND;
  bool heartbeat = now - volLastSend > 5000;   // resend so the Pi syncs after a restart
  if ((moved || heartbeat) && now - volLastSend > 30) {
    Serial.print("V:");
    Serial.println(volSmoothed);
    volSent = volSmoothed;
    volLastSend = now;
  }
}

// Standalone test: comment these out when merging.
void setup() { volumeSetup(); }
void loop() { volumeLoop(); delay(5); }
