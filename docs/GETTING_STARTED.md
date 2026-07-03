# Getting started

Setup only — for daily operation see **[USER_GUIDE.md](USER_GUIDE.md)**.

## Prerequisites

ESP32-S3-DevKitC-1, 4× stepper drivers, 24 V PSU, PC on same WiFi as ESP32, Python 3.11+, PlatformIO.

## 1. Wire

Follow **[../WIRING.md](../WIRING.md)** (active GPIO map at top). Set driver DIP switches with power off. Leave ENA unconnected.

Optional bench test:

```powershell
cd esp32_limit_switch_test
pio run -t upload
```

## 2. Flash firmware

```powershell
cd esp32_dm542_stepper_test
copy include\wifi_secrets.h.example include\wifi_secrets.h
# Edit WIFI_SSID_VALUE, WIFI_PASS_VALUE, MDNS_HOST_VALUE ("arm")
pio run -t upload
```

Verify at `http://arm.local` (or IP from serial monitor). Set `upload_port` in `platformio.ini` if needed.

## 3. Run twin

```powershell
cd arm_twin
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

Open `https://localhost:8000`. Set `esp32_url` in `config.json` if mDNS fails.

**First session:** Twin tab → **Home all** → enable **Live drive**.

Or use **Start Arm Twin.bat** on Windows.

## 4. Wrist camera (optional)

HTTPS is on by default (`ARM_HTTPS=1`). Use the **Phone URL** from the twin sidebar (`https://<PC-LAN-IP>:8000/wrist-camera`).

**iPhone:** accept cert warning in Safari, then Settings → General → About → Certificate Trust Settings → enable dev cert. Certs auto-generate in `arm_twin/certs/`.

Disable HTTPS only for local dev (breaks phone camera): `$env:ARM_HTTPS="0"; python main.py`

Tracking and thumb drive: see [USER_GUIDE.md](USER_GUIDE.md#wrist-camera--tracking).

## Setup troubleshooting

| Problem | Fix |
|---------|-----|
| Twin can't reach ESP32 | Same WiFi, correct `esp32_url`, ping IP |
| Home fails | Limit wiring — [WIRING.md](../WIRING.md) |
| Phone camera blocked | HTTPS Phone URL, trust cert |
