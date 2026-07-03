# API reference

Two HTTP surfaces: the firmware on the ESP32, and the twin server on your PC (which mostly proxies the ESP32 with a bit of extra logic).

## ESP32 (`http://arm.local`)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/status` | Homed flags, steps, degrees |
| `POST` | `/move` | `?m0_deg=…` or step targets |
| `POST` | `/home_all` | Home M2 → M3 → M4 |
| `POST` | `/start` | Jog: `?motor=&dir=cw\|ccw` |
| `POST` | `/stop` | Stop one motor |
| `POST` | `/stop_all` | Emergency stop |
| `POST` | `/calibrate` | Home one motor |
| `GET` | `/settings` | Pulse, delay, invert |

## Twin (`http://localhost:8000`)

Proxied under `/api/*`:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Server status |
| `GET` | `/api/config` | `config.json` |
| `POST` | `/api/config/stick` | Update link lengths / limits |
| `GET` | `/api/status` | ESP32 status |
| `POST` | `/api/home` | Home all |
| `POST` | `/api/move/degrees` | `{"joints": {"M2": 45, …}}` |
| `POST` | `/api/start` | Jog motor |
| `POST` | `/api/stop_all` | Stop all |

Static UI at `/`.
