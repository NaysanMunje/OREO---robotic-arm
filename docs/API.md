# API reference

## ESP32 firmware (`http://arm.local`)

Base URL configurable via `arm_twin/config.json` → `esp32_url`.

### Motion

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/status` | Homed flags, step positions, degrees, homing state |
| `POST` | `/move` | Absolute steps: `?m0=&m1=&m2=&m3=` or `m0_deg`…`m3_deg` |
| `POST` | `/home_all` | Home M2 → M3 → M4 |
| `POST` | `/start` | Jog: `?motor=0-3&dir=cw\|ccw` |
| `POST` | `/stop` | Stop one motor: `?motor=` |
| `POST` | `/stop_all` | Emergency stop all |
| `POST` | `/calibrate` | Home single motor: `?motor=` |

### Settings

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/settings` | Per-motor pulse, delay, invert |
| `POST` | `/settings` | Update: `?motor=&pulse=&delay=&invert=` |

### Diagnostics

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/status_limit` | Limit switch raw state |
| `GET` | `/` | On-device motor test HTML UI |

Motor query index: `0`=M1 wrist, `1`=M2 shoulder, `2`=M3 elbow, `3`=M4 base.

---

## Digital twin (`http://localhost:8000`)

Proxies ESP32 endpoints under `/api/*` and serves the web UI.

### Health & config

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Server version, motor proxy availability |
| `GET` | `/api/config` | Full `config.json` |
| `POST` | `/api/config/stick` | Update procedural link lengths / joint limits |
| `GET` | `/api/network` | PC URL, phone wrist-camera URL, HTTPS note |

### Arm control (proxied)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/status` | ESP32 status JSON |
| `POST` | `/api/home` | `POST /home_all` on ESP32 |
| `POST` | `/api/move` | Step or degree move (body: `MoveRequest`) |
| `POST` | `/api/move/degrees` | `{"joints": {"M2": 45, "M3": 90, ...}}` |
| `GET` | `/api/settings` | Motor settings |
| `POST` | `/api/settings` | Update motor settings |
| `POST` | `/api/start` | Jog motor |
| `POST` | `/api/stop` | Stop motor |
| `POST` | `/api/stop_all` | Stop all |
| `POST` | `/api/calibrate` | Home one joint |

### Wrist camera

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/wrist-camera` | Phone streaming page |
| `GET` | `/api/wrist-camera/status` | Publisher connected, frame count, hand/face/pose flags |
| `GET` | `/api/wrist-camera/frame` | Latest JPEG snapshot |
| `POST` | `/api/wrist-camera/upload` | JPEG body (HTTP fallback) |
| `GET` | `/api/wrist-camera/hand` | Latest hand landmark JSON |
| `POST` | `/api/wrist-camera/hand` | Upload hand landmarks from phone |
| `GET` | `/api/wrist-camera/face` | Latest face landmark JSON |
| `POST` | `/api/wrist-camera/face` | Upload face landmarks from phone |
| `GET` | `/api/wrist-camera/pose` | Latest pose/thumb JSON |
| `POST` | `/api/wrist-camera/pose` | Upload pose/thumb data from phone |
| `WS` | `/ws/wrist-camera` | Binary JPEG + JSON hand/face/pose messages |

**WebSocket roles** (send JSON after connect):

```json
{"role": "publish"}   // phone — sends frames
{"role": "view"}      // PC — receives frames
```

Hand message shape:

```json
{
  "type": "hand",
  "detected": true,
  "hand_count": 1,
  "hands": [[{"x": 0.5, "y": 0.3, "z": -0.1}, ...]],
  "index_tip": {"x": 0.5, "y": 0.3}
}
```

Landmarks are normalized 0–1 in image space (MediaPipe convention).

Pose/thumb message (drives M2/M3 when enabled on PC):

```json
{
  "type": "pose",
  "detected": true,
  "shoulder_deg": 45,
  "elbow_deg": 90
}
```

### Servo (USB — optional)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/servo/status` | Connection state, default port |
| `POST` | `/api/servo/connect` | Open serial (`{"port":"COM5","baud":115200}`) |
| `POST` | `/api/servo/disconnect` | Close serial |
| `POST` | `/api/servo/angle` | Set angle `?deg=0-180` |
| `POST` | `/api/servo/nudge` | Relative move `?delta=` |
| `POST` | `/api/servo/center` | Center servo |
| `POST` | `/api/servo/sweep` | Toggle sweep `?on=true\|false` |

Requires `esp32_servo_test` firmware on USB — separate from WiFi arm motors.

### Static

| Path | Description |
|------|-------------|
| `/` | Main twin UI |
| `/static/*` | JS, hand-track module |
| `/models/*` | FBX/GLB assets |

---

## Environment variables (twin)

| Variable | Default | Description |
|----------|---------|-------------|
| `ESP32_URL` | from `config.json` | Override firmware URL |
| `ARM_HTTPS` | `1` | `0` to disable HTTPS |

CLI: `python main.py --https` forces HTTPS; omit or set `ARM_HTTPS=0` for HTTP only.
