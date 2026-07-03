# Arm digital twin

FastAPI + Three.js UI for the ESP32 arm.

**Docs:** [../docs/USER_GUIDE.md](../docs/USER_GUIDE.md) · [../docs/GETTING_STARTED.md](../docs/GETTING_STARTED.md)

## Run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

Open **http://localhost:8000**. Set `esp32_url` in `config.json` if needed.

## Source

| File | Role |
|------|------|
| `main.py` | FastAPI + ESP32 proxy |
| `config.json` | Joints, links, ESP32 URL |
| `static/index.html` | 3D twin UI |
