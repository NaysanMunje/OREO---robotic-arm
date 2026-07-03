# OREO — 4-DOF Robotic Arm

A DIY WiFi-controlled robotic arm with a browser-based **digital twin** for planning, previewing, and driving moves in real time.

```
┌─────────────┐     WiFi / HTTP      ┌──────────────────┐
│  ESP32-S3   │◄────────────────────►│  PC (arm_twin)   │
│  4× DM542   │      arm.local       │  FastAPI + UI    │
└─────────────┘                      └──────────────────┘
```

<!-- Add a photo or GIF of the arm here:  ![OREO arm](docs/arm.jpg) -->

## Features

- **4 stepper joints** (base, shoulder, elbow, wrist) driven by DM542 microstepping drivers
- **Auto-homing** using limit switches on shoulder, elbow, and base
- **Digital twin** in the browser — 3D stick model, joint sliders, drag-to-move, inverse kinematics
- **Live drive:** the real arm follows the twin (or vice versa) over WiFi
- **HTTP API** on both ESP32 and PC for scripting your own motions
- Runs offline on your local network — no cloud, no accounts

## Hardware you need

- Waveshare **ESP32-S3-DEV-KIT-N8R8** (or compatible ESP32-S3)
- **4× DM542** (or compatible) microstepping drivers
- **4× NEMA-17/23** stepper motors sized to your arm
- **24 V** power supply (sized for your motors × 1.2–1.5)
- **3× limit switches** (normally-open) for shoulder, elbow, and base
- Hookup wire, common ground to ESP32 GND

Detailed pinout in [WIRING.md](WIRING.md).

## Quick start

**Prerequisites:** [PlatformIO](https://platformio.org/install) (or Arduino IDE), Python 3.10+, and a WiFi network the ESP32 can join.

```powershell
# 1. Flash the ESP32
cd esp32_dm542_stepper_test
copy include\wifi_secrets.h.example include\wifi_secrets.h   # then edit SSID + password
pio run -t upload

# 2. Run the digital twin on your PC
cd ..\arm_twin
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

Open **http://localhost:8000** → **Home all** → toggle **Live drive** → move the arm.

Windows users can also double-click **`arm_twin/Start Arm Twin.bat`**.

## Repo layout

| Path | What's inside |
|------|---------------|
| [`arm_twin/`](arm_twin/) | FastAPI server + Three.js browser UI (the digital twin) |
| [`esp32_dm542_stepper_test/`](esp32_dm542_stepper_test/) | Production ESP32 firmware — WiFi, homing, HTTP API |
| [`esp32_limit_switch_test/`](esp32_limit_switch_test/) | Bench sketch for verifying limit-switch wiring |
| [`esp32_s3_test/`](esp32_s3_test/) | Minimal ESP32-S3 bring-up sketch |
| [`docs/`](docs/) | Setup guide, user guide, API reference, architecture |
| [`WIRING.md`](WIRING.md) | GPIO map, driver + limit-switch wiring, DIP settings |

## Documentation

| Doc | For |
|-----|-----|
| [Getting Started](docs/GETTING_STARTED.md) | Wire the arm, flash firmware, run the twin |
| [User Guide](docs/USER_GUIDE.md) | Operate the twin (tabs, IK, homing, troubleshooting) |
| [Architecture](docs/ARCHITECTURE.md) | How the pieces fit together |
| [API Reference](docs/API.md) | HTTP endpoints on the ESP32 and the twin |
| [Wiring](WIRING.md) | GPIO map, pinout, DIP switches |

## License

MIT — see [LICENSE](LICENSE).
