#include <Arduino.h>

// ESP32-S3-DevKitC-1: onboard LED is usually GPIO 48 (RGB) or 38 on some clones
#ifndef LED_BUILTIN
#define LED_BUILTIN 48
#endif

void setup() {
  pinMode(LED_BUILTIN, OUTPUT);
  Serial.begin(115200);
  delay(1500);  // allow USB CDC to connect
  Serial.println();
  Serial.println("=================================");
  Serial.println("  ESP32-S3 board test — running");
  Serial.println("=================================");
  Serial.printf("Chip: %s @ %d MHz\n", ESP.getChipModel(), getCpuFrequencyMhz());
  Serial.printf("Flash: %u bytes\n", ESP.getFlashChipSize());
  Serial.printf("Free heap: %u bytes\n", ESP.getFreeHeap());
}

void loop() {
  static uint32_t count = 0;
  digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN));
  Serial.printf("[%lu] heartbeat — LED toggled\n", ++count);
  delay(1000);
}
