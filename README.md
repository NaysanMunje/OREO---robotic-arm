# 4-DOF Robotic Arm

ESP32-S3 stepper firmware + PC digital twin (3D model, IK, wrist camera, thumb tracking).

```
┌─────────────┐     WiFi / HTTP      ┌──────────────────┐
│  ESP32-S3   │◄────────────────────►│  PC (arm_twin)   │
│  4× DM542   │   arm.local          │  FastAPI + UI    │
└─────────────┘                      └────────┬─────────┘
                                              │
                                     Phone (wrist cam)
```

## Documentation

| Read this | When |
|-----------|------|
| **[docs/GETTING_STARTED.md](docs/GETTING_STARTED.md)** | First-time setup |
| **[docs/USER_GUIDE.md](docs/USER_GUIDE.md)** | Daily use — tabs, IK, camera, diag |
| **[WIRING.md](WIRING.md)** | GPIO, drivers, limits, power |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design |
| [docs/API.md](docs/API.md) | HTTP / WebSocket reference |

Full index: [docs/README.md](docs/README.md)

## Repository

| Path | Role |
|------|------|
| `arm_twin/` | Digital twin server + UI |
| `esp32_dm542_stepper_test/` | Production stepper firmware |
| `esp32_limit_switch_test/` | Limit switch bench test |
| `esp32_servo_test/` | Optional USB servo (separate from arm) |
| `fusion360/` | CAD gear add-in |

## Requirements

Python 3.11+, PlatformIO, ESP32-S3-DevKitC-1, 4× stepper drivers, 24 V PSU, PC on same WiFi as ESP32 and phone.

MIT — see [LICENSE](LICENSE).
