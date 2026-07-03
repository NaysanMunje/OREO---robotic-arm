# ESP32 firmware

WiFi stepper control, limit homing, HTTP API, and on-device web UI.

**Setup:** [../docs/GETTING_STARTED.md](../docs/GETTING_STARTED.md) · **Wiring:** [../WIRING.md](../WIRING.md) · **API:** [../docs/API.md](../docs/API.md)

## Motor map

| Index | Label | PUL | DIR | Limit | Homing |
|-------|-------|-----|-----|-------|--------|
| 0 | M1 wrist | 4 | 5 | — | No |
| 1 | M2 shoulder | 9 | 10 | 7 | Yes |
| 2 | M3 elbow | 11 | 12 | 15 | Yes |
| 3 | M4 base | 13 | 14 | 6 | Yes |

`POST /home_all`: M2 → M3 → M4.

## Flash

```powershell
copy include\wifi_secrets.h.example include\wifi_secrets.h
# edit SSID + password
pio run -t upload
```

Open `http://arm.local` to verify.

## Tuning (`src/main.cpp`)

| Constant | Sync with |
|----------|-----------|
| `STEPS_PER_DEGREE[]` | `arm_twin/config.json` → `steps_per_degree` |
| `MAX_TRAVEL_DEG[]` | `arm_twin/config.json` → joint limits |
| `LIMIT_PIN[]`, `motors[]` | [WIRING.md](../WIRING.md) |

Runtime pulse/delay/invert: web UI `/settings` or twin Motors tab.
