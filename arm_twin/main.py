"""Digital twin server — proxies ESP32 arm API and serves Three.js UI."""

from __future__ import annotations

import json
import os
import socket
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"


def load_config() -> dict[str, Any]:
    with CONFIG_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def esp32_url() -> str:
    return os.environ.get("ESP32_URL", load_config().get("esp32_url", "http://192.168.4.1"))


API_VERSION = "0.2.0-lite"

app = FastAPI(title="Arm Digital Twin", version=API_VERSION)
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")

models_dir = ROOT / "models"
if models_dir.is_dir():
    app.mount("/models", StaticFiles(directory=models_dir), name="models")


class MoveRequest(BaseModel):
    m0: int | None = None
    m1: int | None = None
    m2: int | None = None
    m3: int | None = None
    m0_deg: float | None = None
    m1_deg: float | None = None
    m2_deg: float | None = None
    m3_deg: float | None = None


class MoveDegreesRequest(BaseModel):
    joints: dict[str, float] = Field(default_factory=dict)


class MotorSettingsRequest(BaseModel):
    motor: int = Field(ge=0, le=3)
    delay: int | None = None
    pulse: int | None = None
    invert: int | None = None


class StickModelRequest(BaseModel):
    links_mm: dict[str, float] = Field(default_factory=dict)
    joints: list[dict[str, Any]] = Field(default_factory=list)


def local_lan_ip() -> str | None:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return None


async def esp32_request(method: str, path: str, timeout: float = 3.0, **kwargs: Any) -> httpx.Response:
    url = f"{esp32_url().rstrip('/')}{path}"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            return await client.request(method, url, **kwargs)
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Cannot reach ESP32 at {esp32_url()}: {exc}",
        ) from exc


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


@app.get("/api/network")
async def network_info() -> dict[str, Any]:
    port = int(os.environ.get("ARM_HTTP_PORT", "8000"))
    return {
        "lan_ip": local_lan_ip(),
        "port": port,
        "pc_twin": f"http://localhost:{port}",
    }


@app.get("/api/health")
async def health() -> dict[str, Any]:
    return {
        "ok": True,
        "version": API_VERSION,
        "motor_control": True,
        "esp32_url": esp32_url(),
    }


@app.get("/api/config")
async def get_config() -> dict[str, Any]:
    return load_config()


@app.post("/api/config/stick")
async def save_stick_model(body: StickModelRequest) -> dict[str, Any]:
    cfg = load_config()
    if body.links_mm:
        links = cfg.setdefault("links_mm", {})
        for key, val in body.links_mm.items():
            if not key.startswith("_"):
                links[key] = float(val)
    if body.joints:
        by_label = {j["label"].upper(): j for j in body.joints if j.get("label")}
        for joint in cfg.get("joints", []):
            patch = by_label.get(joint.get("label", "").upper())
            if not patch:
                continue
            if "min_deg" in patch:
                joint["min_deg"] = float(patch["min_deg"])
            if "max_deg" in patch:
                joint["max_deg"] = float(patch["max_deg"])
                joint["home_deg"] = float(patch["max_deg"]) / 2.0
    cfg["model"] = "procedural"
    with CONFIG_PATH.open("w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
        f.write("\n")
    return cfg


@app.get("/api/status")
async def get_status() -> dict[str, Any]:
    resp = await esp32_request("GET", "/status")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    data = resp.json()
    spd = load_config().get("steps_per_degree", [50, 50, 50, 50])
    for motor in data.get("motors", []):
        mid = motor["id"]
        steps = motor.get("steps", 0)
        deg_per = spd[mid] if mid < len(spd) else 50.0
        motor["degrees"] = steps / deg_per if deg_per else 0.0
    return data


@app.post("/api/home")
async def home_all() -> dict[str, str]:
    resp = await esp32_request("POST", "/home_all")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return {"status": "ok"}


@app.post("/api/move")
async def move_steps(body: MoveRequest) -> dict[str, str]:
    params = {k: v for k, v in body.model_dump().items() if v is not None}
    if not params:
        raise HTTPException(status_code=400, detail="No targets specified")
    resp = await esp32_request("POST", "/move", timeout=30.0, params=params)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return {"status": "ok"}


@app.post("/api/move/degrees")
async def move_degrees(body: MoveDegreesRequest) -> dict[str, str]:
    cfg = load_config()
    spd = cfg.get("steps_per_degree", [50, 50, 50, 50])
    label_to_motor = {j["label"].upper(): j["motor"] for j in cfg["joints"]}
    label_to_motor.update({f"M{j['motor']+1}": j["motor"] for j in cfg["joints"]})

    params: dict[str, float] = {}
    for key, deg in body.joints.items():
        motor = label_to_motor.get(key.upper())
        if motor is None and key.lower().startswith("m") and key[1:].isdigit():
            motor = int(key[1:]) - 1
        if motor is None or motor < 0 or motor > 3:
            raise HTTPException(status_code=400, detail=f"Unknown joint: {key}")
        params[f"m{motor}_deg"] = deg

    resp = await esp32_request("POST", "/move", timeout=30.0, params=params)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return {"status": "ok"}


@app.get("/api/settings")
async def get_settings() -> list[dict[str, Any]]:
    resp = await esp32_request("GET", "/settings")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


@app.post("/api/settings")
async def post_settings(body: MotorSettingsRequest) -> dict[str, str]:
    params: dict[str, int] = {"motor": body.motor}
    if body.delay is not None:
        params["delay"] = body.delay
    if body.pulse is not None:
        params["pulse"] = body.pulse
    if body.invert is not None:
        params["invert"] = body.invert
    resp = await esp32_request("POST", "/settings", params=params)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return {"status": "ok"}


@app.post("/api/start")
async def start_motor(motor: int, direction: str = Query("cw", alias="dir")) -> dict[str, str]:
    if motor < 0 or motor > 3:
        raise HTTPException(status_code=400, detail="motor must be 0–3")
    resp = await esp32_request("POST", "/start", params={"motor": motor, "dir": direction})
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return {"status": "ok"}


@app.post("/api/stop")
async def stop_motor(motor: int) -> dict[str, str]:
    if motor < 0 or motor > 3:
        raise HTTPException(status_code=400, detail="motor must be 0–3")
    resp = await esp32_request("POST", "/stop", params={"motor": motor})
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return {"status": "ok"}


@app.post("/api/stop_all")
async def stop_all_motors() -> dict[str, str]:
    resp = await esp32_request("POST", "/stop_all")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return {"status": "ok"}


@app.post("/api/calibrate")
async def calibrate_motor(motor: int) -> dict[str, str]:
    if motor < 0 or motor > 3:
        raise HTTPException(status_code=400, detail="motor must be 0–3")
    resp = await esp32_request("POST", "/calibrate", params={"motor": motor}, timeout=120.0)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("ARM_HTTP_PORT", "8000"))
    print(f"Arm twin v{API_VERSION}")
    print(f"Open: http://localhost:{port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
