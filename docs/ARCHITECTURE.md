# Architecture

## Overview

ESP32 runs real-time stepping and homing. PC twin plans poses (IK, UI) and proxies HTTP — it never touches GPIO. Twin works offline for 3D preview only.

```
Phone ──WS/HTTP──► arm_twin (FastAPI) ──httpx──► ESP32 ──PUL/DIR──► drivers
```

Optional: Servo tab → pyserial → `esp32_servo_test` (USB, independent of WiFi arm).

## Firmware

Arduino on ESP32-S3 · WiFi + mDNS (`arm.local`) · `WebServer` on port 80.

| Index | Motor | Homing | Limit GPIO |
|-------|-------|--------|------------|
| 0 | M1 wrist | No | — |
| 1 | M2 shoulder | Yes | 7 |
| 2 | M3 elbow | Yes | 15 |
| 3 | M4 base | Yes | 6 |

Step counters → degrees via `STEPS_PER_DEGREE[]`. `POST /home_all`: M2 → M3 → M4.

## Digital twin

| Layer | Tech |
|-------|------|
| Server | FastAPI + uvicorn |
| 3D | Three.js (procedural or FBX/GLB) |
| IK | 2-link planar + base rotation; wrist at confirm |
| Sync | Poll `/status` ~2 Hz |
| Wrist cam | WS JPEG relay + MediaPipe JSON (hand/face/pose) |
| TLS | Self-signed dev certs |

### Config sync

`config.json` is the twin source of truth for limits, links, and steps/degree. Match `MAX_TRAVEL_DEG` and `STEPS_PER_DEGREE` in firmware when tuning.

### IK grid

8 height presets (M2/M3 pairs) × 12 M4 angles = 96 FK-validated snap targets. M1 omitted during ring generation; user sets wrist on confirm. Wrist zero stored in browser `localStorage`.

### Wrist camera

Phone publishes JPEG + tracking JSON. PC subscribes via WebSocket (`publish` / `view` roles) or polls REST. Thumb angles map to M2/M3 with 10° snap when live drive is on.

## Security

Self-signed HTTPS for dev only. `wifi_secrets.h` gitignored. ESP32 API has no auth — trusted LAN only.
