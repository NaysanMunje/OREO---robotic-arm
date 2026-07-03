# OREO — Robotic Arm (lite)

4-DOF ESP32 stepper arm + PC **digital twin** (3D model, inverse kinematics, live drive).

```
┌─────────────┐     WiFi / HTTP      ┌──────────────────┐
│  ESP32-S3   │◄────────────────────►│  PC (arm_twin)   │
│  4× DM542   │   arm.local          │  FastAPI + UI    │
└─────────────┘                      └──────────────────┘
```

This is the **lite** branch — no phone camera, hand tracking, or USB servo test code.

| Doc | Contents |
|-----|----------|
| [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md) | Wire → flash → run twin |
| [docs/USER_GUIDE.md](docs/USER_GUIDE.md) | Twin tabs, IK, troubleshooting |
| [WIRING.md](WIRING.md) | GPIO map |

## Quick start

```powershell
cd esp32_dm542_stepper_test
pio run -t upload

cd ..\arm_twin
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

Open **http://localhost:8000** → **Home all** → **Live drive**.

## What's included

- `arm_twin/` — 3D twin UI (Twin, Drive, Motors, Diag tabs)
- `esp32_dm542_stepper_test/` — WiFi stepper firmware
- `docs/`, `WIRING.md`

## Full version

The `main` branch includes wrist camera, thumb tracking, and servo test — kept for local development.
