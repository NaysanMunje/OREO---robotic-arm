# Getting started

Follow these three steps to go from parts on a bench to a homed, driveable arm.

## 1. Wire

Follow **[../WIRING.md](../WIRING.md)**. Set driver DIP switches with power off.

## 2. Flash firmware

```powershell
cd esp32_dm542_stepper_test
copy include\wifi_secrets.h.example include\wifi_secrets.h
pio run -t upload
```

Verify at `http://arm.local`.

## 3. Run twin

```powershell
cd arm_twin
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

Open **http://localhost:8000**. Set `esp32_url` in `config.json` if mDNS fails.

**First session:** Twin tab → **Home all** → **Live drive**.

Or double-click **Start Arm Twin.bat**.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Twin can't reach ESP32 | Same WiFi, correct `esp32_url` |
| Home fails | Limit wiring — [WIRING.md](../WIRING.md) |
