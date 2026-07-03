# Arm digital twin

FastAPI + Three.js UI for the ESP32 arm. **Usage:** [../docs/USER_GUIDE.md](../docs/USER_GUIDE.md) · **Setup:** [../docs/GETTING_STARTED.md](../docs/GETTING_STARTED.md)

## Run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

PC: `https://localhost:8000` · Phone URL in sidebar · `esp32_url` in `config.json`

## Source

| File | Role |
|------|------|
| `main.py` | FastAPI, ESP32 proxy, wrist cam, servo serial |
| `config.json` | Joints, links, ESP32 URL |
| `static/index.html` | Main UI |
| `static/wrist-camera.html` | Phone stream + tracking |
| `static/hand-track.js` | MediaPipe helpers |

## Optional

- **FBX model:** [FUSION_EXPORT.md](FUSION_EXPORT.md) — set `"model": "fbx"` in config
- **Model viewer:** `.\Start Model Viewer.bat` (no ESP32)
- **Tests:** `.\.venv\Scripts\python.exe -m pytest tests/`
