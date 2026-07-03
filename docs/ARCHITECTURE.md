# Architecture

```
PC twin (FastAPI) ──httpx──► ESP32 ──PUL/DIR──► stepper drivers
```

- **Firmware:** WiFi, mDNS (`arm.local`), limit homing M2–M4, HTTP API on port 80
- **Twin:** Three.js procedural model, IK snap grid, polls `/status` ~2 Hz
- **Config:** `config.json` limits/links must match firmware `MAX_TRAVEL_DEG` and `STEPS_PER_DEGREE`

Motor index: 0=M1 wrist, 1=M2 shoulder, 2=M3 elbow, 3=M4 base.
