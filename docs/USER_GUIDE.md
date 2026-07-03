# User guide

Operate the arm after setup ([GETTING_STARTED.md](GETTING_STARTED.md)).

## URLs

| Device | URL |
|--------|-----|
| PC twin | `https://localhost:8000` |
| Phone camera | `https://<PC-LAN-IP>:8000/wrist-camera` |
| ESP32 (direct) | `http://arm.local` |

Homing order: M2 → M3 → M4. M1 (wrist) has no limit — use **Set wrist 0°** for a software reference.

## Typical session

1. `python main.py` in `arm_twin/`
2. Open twin → green connection dot
3. **Home all** → enable **Live drive**
4. Move via sliders, 3D drag, IK, or thumb control

**Stop:** **Stop all** on Twin or Drive tab.

**0° convention (M2–M4):** 0° = limit switch. Vertical ≈ half of max travel.

## Twin tab

### 3D viewer

Orbit (left-drag) · pan (right-drag) · zoom (scroll). Drag joint spheres to pose. **Red line** = phone bottom / M1 axis.

### Inverse kinematics

1. Enable **IK click**
2. Pick a colored dot (8 height rings × 12 base angles)
3. Filter by ring or **All heights**
4. Hover → preview → set **Phone rotation** → **Move arm here**
5. **Set wrist 0°** with phone mounted along the red line

IK solves M2/M3/M4; wrist rotation is set at confirm.

### Wrist camera & tracking

Phone: open **Phone URL** → **Start camera & stream**.

| Phone toggle | Effect |
|--------------|--------|
| Track hands | Skeleton on phone + PC |
| Track thumb | Knuckle angles → M2/M3 (with PC toggle below) |
| Track face | Face mesh |
| Rear camera | Typical wrist mount |
| Dim screen | Battery saver |

PC: **Drive shoulder + elbow from thumb** (needs homed + live drive). Invert toggles fix reversed motion. 10° snap reduces jitter.

### Stick model

Edit link lengths (mm) and joint limits → **Save & rebuild model**. Sync limit changes with firmware `MAX_TRAVEL_DEG` in `main.cpp`.

## Other tabs

| Tab | Use |
|-----|-----|
| **Drive** | Absolute step targets per motor (`m0`–`m3`) |
| **Motors** | Jog CW/CCW, pulse/delay, invert, single-motor calibrate |
| **Diag** | Live GPIO/limit/steps table; ~1.5 s jog tests per motor |
| **Servo** | USB hobby servo via `esp32_servo_test` — **not** the WiFi arm motors |

### Diag jog test results

| Result | Likely cause |
|--------|----------------|
| Steps ↑, shaft moves | OK |
| Steps ↑, shaft still | Driver ENA, phases, or 24 V to that driver |
| Steps unchanged | GPIO / wiring / firmware |
| Limit always pressed | Short to GND or stuck switch |

### Servo tab

Flash `esp32_servo_test`, connect COM port (default in `config.json`). Only one app can hold the port — close monitor before flashing.

## Configuration

**`arm_twin/config.json`:** `esp32_url`, `joints[]`, `links_mm`, `steps_per_degree`, `wrist.steps_per_90`, `model`, `servo.port`.

**Firmware `main.cpp`:** keep `STEPS_PER_DEGREE`, `MAX_TRAVEL_DEG`, GPIO map in sync with config and [WIRING.md](../WIRING.md).

| Env var | Default | Effect |
|---------|---------|--------|
| `ARM_HTTPS` | `1` | `0` = HTTP only (no iPhone camera) |
| `ESP32_URL` | from config | Override firmware URL |

## Troubleshooting

| Problem | Fix |
|---------|-----|
| No connection | WiFi, `esp32_url`, ping ESP32 |
| Live drive off | Home all first |
| IK dots missing | Hard-refresh, enable IK mode |
| Phone camera blocked | HTTPS + cert trust, not localhost on phone |
| Thumb no motion | Track thumb on phone + PC toggle + homed + live drive |
| COM5 busy | Close serial monitor / Servo tab before flash |
| Model ≠ real arm | Re-home; check `steps_per_degree` and link lengths |
