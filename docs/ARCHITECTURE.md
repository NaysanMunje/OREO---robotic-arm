# Architecture

## Request flow

```
Browser (Three.js UI)
      │  fetch /api/*
      ▼
PC twin server  (arm_twin/main.py — FastAPI + httpx)
      │  HTTP over WiFi
      ▼
ESP32 firmware  (firmware/ — mDNS "arm.local")
      │  GPIO PUL/DIR
      ▼
4× DM542 drivers → 4× stepper motors
```

- The browser talks only to the twin server (`/api/*`), which forwards to the ESP32. This lets the UI stay simple and gives you one place to add higher-level features (like inverse kinematics).
- The ESP32 exposes its own HTTP API (`/status`, `/move`, `/home_all`, …) that you can hit directly from `curl`, scripts, or another host — see [API.md](API.md).
- Limit switches on M2 / M3 / M4 provide absolute references; M1 (wrist) is open-loop and uses a user-set software zero.

## Motor index

| Index | Label | Role | Limit switch |
|-------|-------|------|--------------|
| 0 | M1 | Wrist | none |
| 1 | M2 | Shoulder | yes |
| 2 | M3 | Elbow | yes |
| 3 | M4 | Base | yes |

## Where to look

| Concern | File |
|---------|------|
| Firmware stepping / homing | [`firmware/src/main.cpp`](../firmware/src/main.cpp) |
| GPIO / driver / limit wiring | [`WIRING.md`](../WIRING.md) |
| Twin HTTP server | [`arm_twin/main.py`](../arm_twin/main.py) |
| Twin browser UI (3D, sliders, IK) | [`arm_twin/static/index.html`](../arm_twin/static/index.html) |
| Twin config (joints, links, ESP32 URL) | [`arm_twin/config.json`](../arm_twin/config.json) |

## Keep in sync

Two places store per-joint constants and both need to match, or the twin will display something different from what the arm actually does:

| Twin (`arm_twin/config.json`) | Firmware (`firmware/src/main.cpp`) |
|-------------------------------|-----------------------------------------------------|
| `steps_per_degree[]` | `STEPS_PER_DEGREE[]` |
| joint `min_deg` / `max_deg` | `MAX_TRAVEL_DEG[]` |

The twin polls `/status` from the ESP32 roughly twice a second to keep the on-screen model up to date.
