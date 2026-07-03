# Wiring

**Board:** [Waveshare ESP32-S3-DEV-KIT-N8R8](https://www.waveshare.com/wiki/ESP32-S3-DEV-KIT-N8R8) (DevKitC-1 compatible)  
**Control:** common-cathode — GPIO → PUL+/DIR+, GND → PUL−/DIR−  
**Firmware:** `esp32_dm542_stepper_test/src/main.cpp`

## GPIO map

| Motor | Joint | PUL | DIR | Limit | Homing |
|-------|-------|-----|-----|-------|--------|
| M1 | Wrist | **4** | **5** | — | No |
| M2 | Shoulder | **9** | **10** | **7** | Yes |
| M3 | Elbow | **11** | **12** | **15** | Yes |
| M4 | Base | **13** | **14** | **6** | Yes |

```
Limit:   GPIO ── switch (NO) ── GND     (open = HIGH, pressed = LOW)
Driver:  GPIO → PUL+/DIR+    GND → PUL−/DIR−
Power:   24V+ → V+           24V− → V− (tie to ESP GND)
ENA:     leave unconnected
```

Route PUL/DIR to upper J1 header pins; limits to lower J1 / J3 where possible.

## GPIO — do not use

| GPIO | Reason |
|------|--------|
| 0 | Boot strapping |
| 19, 20 | USB |
| 43, 44 | UART / strapping |
| 45, 46 | Strapping |
| 48 | Onboard RGB LED |

## Shared ground

```
ESP32 GND (J1-22, J3-1/21/22)
  ├── all driver DIR−, PUL−, GND
  ├── limit switches (GND side)
  └── 24V PSU negative
```

## Driver wiring (×4)

```
ESP32 GPIO (DIR) ──► DIR+
ESP32 GPIO (PUL) ──► PUL+
ESP32 GND        ──► DIR−, PUL−, GND
```

| PSU | Each driver |
|-----|-------------|
| + | V+ |
| − | V− (common GND above) |

USB powers ESP32 only. Size PSU: sum of motor amps × 1.2–1.5.

## Motor → driver (4 wires)

Find coil pairs with a multimeter. Example (motor 1):

| Wire | Terminal |
|------|----------|
| Blue | A+ |
| Red | A− |
| Black | B+ |
| Green | B− |

## Driver DIP (power off)

Match nameplate current. Microstepping 1/8 or 1/16. DM542 (8 DIP) and TB6600/Meccanixity (6 DIP) use different tables.

## Bench test limits

```powershell
cd esp32_limit_switch_test
pio run -t upload
```

## Troubleshooting

| Issue | Check |
|-------|--------|
| One motor dead | GPIO wire, common GND, driver DIP |
| Wrong motor moves | GPIO mix-up — table above |
| Limit always pressed | Short to GND, stuck switch |
| Limit never pressed | Wrong GPIO, not NO, no GND |
| ESP32 won't boot | GPIO 0 / 46 / strapping shorted |
