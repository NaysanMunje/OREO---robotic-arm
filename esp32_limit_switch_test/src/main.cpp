/*
 * ESP32-S3 — basic limit switch test (no motors)
 * Waveshare ESP32-S3-DEV-KIT-N8R8 / DevKitC-1 pinout (USB at bottom)
 *
 * Limits on lower header pins:
 *   J1 LIM=14 (J1-20)  J2 LIM=13 (J1-19)  J3 LIM=12 (J1-18)  J4 LIM=21 (J3-18)
 * WiFi: ESP32-Arm / stepper123  ->  http://192.168.4.1
 */

#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>

static const uint8_t NUM_SWITCHES = 4;

struct LimitSwitch {
  uint8_t pin;
  const char *name;
  const char *headerPin;
};

const LimitSwitch limits[NUM_SWITCHES] = {
    {14, "J1 Base", "J1-20"},
    {13, "J2 Shoulder", "J1-19"},
    {12, "J3 Elbow", "J1-18"},
    {21, "J4 Wrist", "J3-18"},
};

const char *AP_SSID = "ESP32-Arm";
const char *AP_PASS = "stepper123";

WebServer server(80);

bool isPressed(uint8_t pin) { return digitalRead(pin) == LOW; }

const char INDEX_HTML[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Limit Switch Test</title>
<style>
body{margin:0;min-height:100vh;font-family:system-ui,sans-serif;background:#111;color:#eee;padding:1rem}
h1{font-size:1.2rem;margin:0 0 .25rem}
.sub{color:#888;font-size:.85rem;margin:0 0 1rem}
.row{max-width:360px;margin:0 auto .6rem;padding:.9rem 1rem;background:#1a1a1a;border-radius:10px;display:flex;justify-content:space-between;align-items:center}
.name{font-weight:600}
.pin{font-size:.75rem;color:#666;margin-top:.15rem}
.ok{color:#4ade80}.hit{color:#f87171;font-weight:700}
</style></head><body>
<h1>Limit switch test</h1>
<p class="sub">Open = idle · Pressed = at home</p>
<div id="list"></div>
<script>
const joints=[
  {n:'J1 Base',p:'GPIO 14 (J1-20)'},
  {n:'J2 Shoulder',p:'GPIO 13 (J1-19)'},
  {n:'J3 Elbow',p:'GPIO 12 (J1-18)'},
  {n:'J4 Wrist',p:'GPIO 21 (J3-18)'}
];
const list=document.getElementById('list');
async function poll(){
  const r=await fetch('/status');const d=await r.json();
  list.innerHTML=joints.map((j,i)=>{
    const hit=d[i];
    return `<div class="row"><div><div class="name">${j.n}</div><div class="pin">${j.p}</div></div><div class="${hit?'hit':'ok'}">${hit?'PRESSED':'open'}</div></div>`;
  }).join('');
}
setInterval(poll,200);poll();
</script></body></html>
)rawliteral";

void setup() {
  Serial.begin(115200);
  for (uint8_t i = 0; i < NUM_SWITCHES; i++) {
    pinMode(limits[i].pin, INPUT_PULLUP);
  }

  WiFi.mode(WIFI_AP);
  WiFi.softAP(AP_SSID, AP_PASS);

  Serial.println("\n=== Limit switch test ===");
  Serial.println("Pressed = LOW (switch to GND)");
  for (uint8_t i = 0; i < NUM_SWITCHES; i++) {
    Serial.printf("  %s -> GPIO %u (%s)\n", limits[i].name, limits[i].pin, limits[i].headerPin);
  }
  Serial.print("http://");
  Serial.println(WiFi.softAPIP());

  server.on("/", []() { server.send_P(200, "text/html", INDEX_HTML); });
  server.on("/status", []() {
    String json = "[";
    for (uint8_t i = 0; i < NUM_SWITCHES; i++) {
      if (i) json += ',';
      json += isPressed(limits[i].pin) ? "true" : "false";
    }
    json += "]";
    server.send(200, "application/json", json);
  });
  server.begin();
}

void loop() {
  server.handleClient();

  static uint32_t lastPrint = 0;
  if (millis() - lastPrint >= 500) {
    lastPrint = millis();
    for (uint8_t i = 0; i < NUM_SWITCHES; i++) {
      Serial.printf("%s (GPIO %u): %s\n", limits[i].name, limits[i].pin,
                    isPressed(limits[i].pin) ? "PRESSED" : "open");
    }
    Serial.println();
  }
}
