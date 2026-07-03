# Getting started

Wire the arm, flash firmware, and run the digital twin.

## Prerequisites

- [PlatformIO](https://platformio.org/install) (or Arduino IDE)
- Python 3.10+
- A WiFi network the ESP32 can join

## Hardware

- Waveshare **ESP32-S3-DEV-KIT-N8R8** (or compatible ESP32-S3)
- **4× DM542** (or compatible) microstepping drivers
- **4× NEMA-17/23** stepper motors sized to your arm
- **24 V** power supply (sized for your motors × 1.2–1.5)
- **3× limit switches** (normally-open) for shoulder, elbow, and base
- Hookup wire, common ground to ESP32 GND

Pinout and driver wiring: **[../WIRING.md](../WIRING.md)**.

## 1. Wire

Follow **[../WIRING.md](../WIRING.md)**. Set driver DIP switches with power off.

## 2. Flash firmware

```powershell
cd firmware
copy include\wifi_secrets.h.example include\wifi_secrets.h
# edit wifi_secrets.h with your SSID and password
pio run -t upload
```

Verify at `http://arm.local`.

## 3. Run the digital twin

```powershell
cd arm_twin
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

Open **http://localhost:8000**. Set `esp32_url` in `config.json` if mDNS fails.

**First session:** Twin tab → **Home all** → **Live drive**.

On Windows you can also double-click **`arm_twin/Start Arm Twin.bat`**.

## Features

- **4 stepper joints** (base, shoulder, elbow, wrist) driven by DM542 microstepping drivers
- **Auto-homing** using limit switches on shoulder, elbow, and base
- **Digital twin** in the browser — 3D stick model, joint sliders, drag-to-move, inverse kinematics
- **Live drive:** the real arm follows the twin over WiFi
- **HTTP API** on both ESP32 and PC for scripting motions
- Runs offline on your local network — no cloud, no accounts

## Repo layout

| Path | What's inside |
|------|---------------|
| [`firmware/`](../firmware/) | ESP32 firmware — WiFi, motors, homing, HTTP API |
| [`arm_twin/`](../arm_twin/) | FastAPI server + Three.js browser UI |
| [`docs/`](./) | Setup, user guide, API, architecture |
| [`WIRING.md`](../WIRING.md) | GPIO map, driver + limit-switch wiring |

## More docs

| Doc | For |
|-----|-----|
| [User Guide](USER_GUIDE.md) | Operate the twin (tabs, IK, homing, troubleshooting) |
| [Architecture](ARCHITECTURE.md) | How the pieces fit together |
| [API Reference](API.md) | HTTP endpoints on the ESP32 and the twin |
| [Wiring](../WIRING.md) | GPIO map, pinout, DIP switches |

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Twin can't reach ESP32 | Same WiFi, correct `esp32_url` in `config.json` |
| Home fails | Limit wiring — [WIRING.md](../WIRING.md) |
