# User guide

Operate the arm after setup ([GETTING_STARTED.md](GETTING_STARTED.md)).

## URLs

| Device | URL |
|--------|-----|
| PC twin | `http://localhost:8000` |
| ESP32 (direct) | `http://arm.local` |

Homing order: M2 → M3 → M4. M1 (wrist) has no limit — use **Set wrist 0°** for a software reference.

## Typical session

1. `python main.py` in `arm_twin/`
2. Open twin → green connection dot
3. **Home all** → enable **Live drive**
4. Move via sliders, 3D drag, or IK

**Stop:** **Stop all** on Twin or Drive tab.

## Twin tab

- **3D viewer:** orbit, drag joint spheres. **Red line** = wrist axis (M1).
- **IK:** enable IK click → pick dot → set **Wrist rotation** → **Move arm here**
- **Set wrist 0°:** align tool along red line, then set zero
- **Stick model:** edit link lengths (mm) and limits → **Save & rebuild model**

## Other tabs

| Tab | Use |
|-----|-----|
| **Drive** | Absolute step targets per motor |
| **Motors** | Jog, pulse/delay, invert, calibrate |
| **Diag** | GPIO/limit status, per-motor jog tests |

## Configuration

**`config.json`:** `esp32_url`, `joints[]`, `links_mm`, `steps_per_degree`, `wrist.steps_per_90`

Keep firmware `STEPS_PER_DEGREE` and `MAX_TRAVEL_DEG` in sync.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| No connection | WiFi, `esp32_url`, ping ESP32 |
| Live drive off | Home all first |
| IK dots missing | Hard-refresh, enable IK mode |
| Model ≠ real arm | Re-home; check `steps_per_degree` and link lengths |
