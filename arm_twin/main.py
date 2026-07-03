"""Digital twin server — proxies ESP32 arm API and serves Three.js UI."""

from __future__ import annotations

import asyncio
import json
import os
import re
import socket
import threading
import time
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"

# Wrist camera relay: one phone publisher → many PC viewers
_wrist_publisher: WebSocket | None = None
_wrist_viewers: set[WebSocket] = set()
_wrist_latest_jpeg: bytes | None = None
_wrist_frame_count = 0
_wrist_last_frame_at: float | None = None
_wrist_hand_state: dict[str, Any] | None = None
_wrist_hand_at: float | None = None
_wrist_face_state: dict[str, Any] | None = None
_wrist_face_at: float | None = None
_wrist_pose_state: dict[str, Any] | None = None
_wrist_pose_at: float | None = None


def load_config() -> dict[str, Any]:
    with CONFIG_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def esp32_url() -> str:
    return os.environ.get("ESP32_URL", load_config().get("esp32_url", "http://192.168.4.1"))


try:  # pyserial is optional; servo page degrades gracefully without it
    import serial as _pyserial
    from serial.tools import list_ports as _list_ports
except ImportError:  # pragma: no cover
    _pyserial = None
    _list_ports = None


class ServoLink:
    """Talks to the ESP32 servo-test firmware over USB serial."""

    def __init__(self) -> None:
        self._ser: Any = None
        self.port: str | None = None
        self.baud: int = 115200
        self.angle: int = 90
        self.sweeping: bool = False
        self._lock = threading.Lock()

    @staticmethod
    def available() -> bool:
        return _pyserial is not None

    def available_ports(self) -> list[str]:
        if _list_ports is None:
            return []
        return [p.device for p in _list_ports.comports()]

    def is_connected(self) -> bool:
        return self._ser is not None and getattr(self._ser, "is_open", False)

    def _close_locked(self) -> None:
        if self._ser is not None:
            try:
                self._ser.close()
            except Exception:
                pass
        self._ser = None

    def open(self, port: str, baud: int = 115200) -> None:
        if _pyserial is None:
            raise RuntimeError("pyserial is not installed on the server")
        with self._lock:
            self._close_locked()
            self._ser = _pyserial.Serial(port, baud, timeout=0.2)
            self.port = port
            self.baud = baud
            time.sleep(0.4)  # ESP32 resets when the port opens
            try:
                self._ser.reset_input_buffer()
            except Exception:
                pass

    def close(self) -> None:
        with self._lock:
            self._close_locked()
            self.sweeping = False

    def _read_replies_locked(self) -> list[str]:
        lines: list[str] = []
        deadline = time.time() + 0.2
        try:
            while time.time() < deadline:
                raw = self._ser.readline()
                if not raw:
                    break
                line = raw.decode(errors="replace").strip()
                if not line:
                    continue
                lines.append(line)
                m = re.match(r"POS\s+(\d+)", line, re.IGNORECASE)
                if m:
                    self.angle = max(0, min(180, int(m.group(1))))
        except Exception:
            pass
        return lines

    def send(self, cmd: str) -> list[str]:
        with self._lock:
            if not self.is_connected():
                raise RuntimeError("Servo not connected")
            self._ser.write((cmd + "\n").encode())
            self._ser.flush()
            return self._read_replies_locked()

    def status(self) -> dict[str, Any]:
        return {
            "available": self.available(),
            "connected": self.is_connected(),
            "port": self.port,
            "baud": self.baud,
            "angle": self.angle,
            "sweeping": self.sweeping,
            "ports": self.available_ports(),
        }


servo_link = ServoLink()


def servo_default_port() -> str:
    cfg = load_config().get("servo", {})
    return os.environ.get("SERVO_PORT", cfg.get("port", "COM5"))


def servo_default_baud() -> int:
    cfg = load_config().get("servo", {})
    return int(os.environ.get("SERVO_BAUD", cfg.get("baud", 115200)))


API_VERSION = "0.2.0"

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
    joints: dict[str, float] = Field(
        default_factory=dict,
        description="Motor labels or indices, e.g. {'M2': 45, 'm1': 10}",
    )


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


_NO_CACHE = {"Cache-Control": "no-cache, must-revalidate"}


@app.get("/wrist-camera")
async def wrist_camera_page() -> FileResponse:
    """Phone page — mount on wrist, stream camera to the PC twin."""
    return FileResponse(
        ROOT / "static" / "wrist-camera.html",
        headers=_NO_CACHE,
    )


@app.get("/api/wrist-camera/status")
async def wrist_camera_status() -> dict[str, Any]:
    age = None
    if _wrist_last_frame_at is not None:
        age = round(time.time() - _wrist_last_frame_at, 1)
    return {
        "publisher_connected": _wrist_publisher is not None,
        "viewer_count": len(_wrist_viewers),
        "has_frame": _wrist_latest_jpeg is not None,
        "frame_count": _wrist_frame_count,
        "seconds_since_frame": age,
        "hand_detected": bool(_wrist_hand_state and _wrist_hand_state.get("detected")),
        "hand_count": (_wrist_hand_state or {}).get("hand_count", 0),
        "face_detected": bool(_wrist_face_state and _wrist_face_state.get("detected")),
        "face_count": (_wrist_face_state or {}).get("face_count", 0),
        "pose_detected": bool(_wrist_pose_state and _wrist_pose_state.get("detected")),
    }


class HandTrackPayload(BaseModel):
    detected: bool = False
    hand_count: int = 0
    hands: list[list[dict[str, float]]] = Field(default_factory=list)
    index_tip: dict[str, float] | None = None


class FaceTrackPayload(BaseModel):
    detected: bool = False
    face_count: int = 0
    faces: list[list[dict[str, float]]] = Field(default_factory=list)
    nose_tip: dict[str, float] | None = None


class PoseTrackPayload(BaseModel):
    detected: bool = False
    side: str | None = None
    shoulder_angle: float | None = None
    elbow_angle: float | None = None
    points: dict[str, dict[str, float] | None] | None = None


async def _broadcast_hand_state(data: dict[str, Any]) -> None:
    global _wrist_hand_state, _wrist_hand_at
    _wrist_hand_state = data
    _wrist_hand_at = time.time()
    msg = json.dumps({"type": "hand", **data})
    dead: list[WebSocket] = []
    for viewer in _wrist_viewers:
        try:
            await viewer.send_text(msg)
        except Exception:
            dead.append(viewer)
    for viewer in dead:
        _wrist_viewers.discard(viewer)


async def _broadcast_face_state(data: dict[str, Any]) -> None:
    global _wrist_face_state, _wrist_face_at
    _wrist_face_state = data
    _wrist_face_at = time.time()
    msg = json.dumps({"type": "face", **data})
    dead: list[WebSocket] = []
    for viewer in _wrist_viewers:
        try:
            await viewer.send_text(msg)
        except Exception:
            dead.append(viewer)
    for viewer in dead:
        _wrist_viewers.discard(viewer)


async def _broadcast_pose_state(data: dict[str, Any]) -> None:
    global _wrist_pose_state, _wrist_pose_at
    _wrist_pose_state = data
    _wrist_pose_at = time.time()
    msg = json.dumps({"type": "pose", **data})
    dead: list[WebSocket] = []
    for viewer in _wrist_viewers:
        try:
            await viewer.send_text(msg)
        except Exception:
            dead.append(viewer)
    for viewer in dead:
        _wrist_viewers.discard(viewer)


@app.get("/api/wrist-camera/hand")
async def wrist_camera_hand() -> dict[str, Any]:
    if not _wrist_hand_state:
        return {"detected": False, "hand_count": 0, "hands": [], "age_sec": None}
    age = None
    if _wrist_hand_at is not None:
        age = round(time.time() - _wrist_hand_at, 2)
    return {**_wrist_hand_state, "age_sec": age}


@app.post("/api/wrist-camera/hand")
async def wrist_camera_hand_upload(body: HandTrackPayload) -> dict[str, str]:
    await _broadcast_hand_state(body.model_dump())
    return {"status": "ok"}


@app.get("/api/wrist-camera/face")
async def wrist_camera_face() -> dict[str, Any]:
    if not _wrist_face_state:
        return {"detected": False, "face_count": 0, "faces": [], "age_sec": None}
    age = None
    if _wrist_face_at is not None:
        age = round(time.time() - _wrist_face_at, 2)
    return {**_wrist_face_state, "age_sec": age}


@app.post("/api/wrist-camera/face")
async def wrist_camera_face_upload(body: FaceTrackPayload) -> dict[str, str]:
    await _broadcast_face_state(body.model_dump())
    return {"status": "ok"}


@app.get("/api/wrist-camera/pose")
async def wrist_camera_pose() -> dict[str, Any]:
    if not _wrist_pose_state:
        return {
            "detected": False,
            "side": None,
            "shoulder_angle": None,
            "elbow_angle": None,
            "points": None,
            "age_sec": None,
        }
    age = None
    if _wrist_pose_at is not None:
        age = round(time.time() - _wrist_pose_at, 2)
    return {**_wrist_pose_state, "age_sec": age}


@app.post("/api/wrist-camera/pose")
async def wrist_camera_pose_upload(body: PoseTrackPayload) -> dict[str, str]:
    await _broadcast_pose_state(body.model_dump())
    return {"status": "ok"}


# --- Servo (USB serial) -----------------------------------------------------

class ServoConnectRequest(BaseModel):
    port: str | None = None
    baud: int | None = None


@app.get("/api/servo/status")
async def servo_status() -> dict[str, Any]:
    st = servo_link.status()
    st["default_port"] = servo_default_port()
    return st


@app.post("/api/servo/connect")
async def servo_connect(body: ServoConnectRequest | None = None) -> dict[str, Any]:
    if not ServoLink.available():
        raise HTTPException(status_code=503, detail="pyserial not installed — run: pip install pyserial")
    port = (body.port if body else None) or servo_default_port()
    baud = (body.baud if body else None) or servo_default_baud()
    try:
        await asyncio.to_thread(servo_link.open, port, baud)
        await asyncio.to_thread(servo_link.send, "?")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Could not open {port}: {exc}") from exc
    return servo_link.status()


@app.post("/api/servo/disconnect")
async def servo_disconnect() -> dict[str, Any]:
    await asyncio.to_thread(servo_link.close)
    return servo_link.status()


@app.post("/api/servo/angle")
async def servo_angle(deg: int = Query(ge=0, le=180)) -> dict[str, Any]:
    servo_link.sweeping = False
    try:
        await asyncio.to_thread(servo_link.send, f"A{deg}")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return servo_link.status()


@app.post("/api/servo/nudge")
async def servo_nudge(delta: int = Query(ge=-180, le=180)) -> dict[str, Any]:
    servo_link.sweeping = False
    cmd = f"+{delta}" if delta >= 0 else f"-{abs(delta)}"
    try:
        await asyncio.to_thread(servo_link.send, cmd)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return servo_link.status()


@app.post("/api/servo/center")
async def servo_center() -> dict[str, Any]:
    servo_link.sweeping = False
    try:
        await asyncio.to_thread(servo_link.send, "C")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return servo_link.status()


@app.post("/api/servo/sweep")
async def servo_sweep(on: bool = Query(True)) -> dict[str, Any]:
    try:
        await asyncio.to_thread(servo_link.send, "S" if on else "X")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    servo_link.sweeping = on
    return servo_link.status()


@app.post("/api/wrist-camera/upload")
async def wrist_camera_upload(request: Request) -> dict[str, str]:
    """HTTP fallback for phone uploads when WebSocket is blocked."""
    data = await request.body()
    if len(data) < 200:
        raise HTTPException(status_code=400, detail="Frame too small or empty")
    await _broadcast_wrist_frame(data)
    return {"status": "ok"}


@app.get("/api/wrist-camera/frame")
async def wrist_camera_frame() -> Response:
    if not _wrist_latest_jpeg:
        raise HTTPException(status_code=404, detail="No frame yet — start wrist camera on phone")
    return Response(content=_wrist_latest_jpeg, media_type="image/jpeg")


async def _broadcast_wrist_frame(data: bytes) -> None:
    global _wrist_latest_jpeg, _wrist_frame_count, _wrist_last_frame_at
    _wrist_latest_jpeg = data
    _wrist_frame_count += 1
    _wrist_last_frame_at = time.time()
    dead: list[WebSocket] = []
    for viewer in _wrist_viewers:
        try:
            await viewer.send_bytes(data)
        except Exception:
            dead.append(viewer)
    for viewer in dead:
        _wrist_viewers.discard(viewer)


@app.websocket("/ws/wrist-camera")
async def wrist_camera_ws(ws: WebSocket) -> None:
    global _wrist_publisher
    await ws.accept()
    role: str | None = None
    try:
        hello = await ws.receive_text()
        msg = json.loads(hello)
        role = msg.get("role")

        if role == "publish":
            if _wrist_publisher is not None:
                await ws.send_json({"type": "error", "message": "Another phone is already streaming"})
                await ws.close()
                return
            _wrist_publisher = ws
            await ws.send_json({"type": "ready"})
            if _wrist_hand_state:
                await ws.send_json({"type": "hand", **_wrist_hand_state})
            if _wrist_face_state:
                await ws.send_json({"type": "face", **_wrist_face_state})
            if _wrist_pose_state:
                await ws.send_json({"type": "pose", **_wrist_pose_state})
            while True:
                incoming = await ws.receive()
                if incoming.get("type") == "websocket.disconnect":
                    break
                data = incoming.get("bytes")
                if data:
                    await _broadcast_wrist_frame(data)
                text = incoming.get("text")
                if text:
                    try:
                        msg = json.loads(text)
                        if msg.get("type") == "hand":
                            data = {k: v for k, v in msg.items() if k != "type"}
                            await _broadcast_hand_state(data)
                        elif msg.get("type") == "face":
                            data = {k: v for k, v in msg.items() if k != "type"}
                            await _broadcast_face_state(data)
                        elif msg.get("type") == "pose":
                            data = {k: v for k, v in msg.items() if k != "type"}
                            await _broadcast_pose_state(data)
                    except json.JSONDecodeError:
                        pass

        elif role == "view":
            _wrist_viewers.add(ws)
            await ws.send_json({"type": "ready", "has_frame": _wrist_latest_jpeg is not None})
            if _wrist_latest_jpeg:
                await ws.send_bytes(_wrist_latest_jpeg)
            if _wrist_hand_state:
                await ws.send_json({"type": "hand", **_wrist_hand_state})
            if _wrist_face_state:
                await ws.send_json({"type": "face", **_wrist_face_state})
            if _wrist_pose_state:
                await ws.send_json({"type": "pose", **_wrist_pose_state})
            while True:
                incoming = await ws.receive()
                if incoming.get("type") == "websocket.disconnect":
                    break

        else:
            await ws.send_json({"type": "error", "message": "role must be publish or view"})
            await ws.close()

    except WebSocketDisconnect:
        pass
    finally:
        if role == "publish" and _wrist_publisher is ws:
            _wrist_publisher = None
        elif role == "view":
            _wrist_viewers.discard(ws)


@app.get("/api/network")
async def network_info(request: Request) -> dict[str, Any]:
    """URLs for phone vs PC — localhost on a phone means the phone itself, not this PC."""
    ip = local_lan_ip()
    port = request.url.port or 8000
    scheme = request.url.scheme
    host_base = f"{scheme}://{ip}:{port}" if ip else None
    local_base = f"{scheme}://localhost:{port}"
    return {
        "lan_ip": ip,
        "port": port,
        "scheme": scheme,
        "https": scheme == "https",
        "pc_twin": local_base,
        "phone_twin": host_base,
        "phone_wrist_camera": f"{host_base}/wrist-camera" if host_base else None,
        "iphone_note": (
            "On iPhone: open the HTTPS phone link in Safari, tap through the certificate warning, "
            "then allow camera access."
            if scheme == "https"
            else "iPhone needs HTTPS — restart server with: python main.py --https"
        ),
    }


@app.get("/api/health")
async def health() -> dict[str, Any]:
    """Probe this endpoint to confirm the twin server includes motor-control proxies."""
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
    """Update stick-model dimensions and joint limits in config.json."""
    cfg = load_config()
    if body.links_mm:
        links = cfg.setdefault("links_mm", {})
        for key, val in body.links_mm.items():
            if key.startswith("_"):
                continue
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
    cfg = load_config()
    spd = cfg.get("steps_per_degree", [50, 50, 50, 50])
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
async def start_motor(
    motor: int,
    direction: str = Query("cw", alias="dir"),
) -> dict[str, str]:
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
    import sys

    import uvicorn

    use_https = "--https" in sys.argv or os.environ.get("ARM_HTTPS", "1") == "1"
    ssl_kwargs: dict[str, str] = {}

    if use_https:
        try:
            from ssl_certs import ensure_dev_cert, local_lan_ip as cert_lan_ip

            cert_path, key_path = ensure_dev_cert(ROOT / "certs")
            ssl_kwargs = {"ssl_certfile": str(cert_path), "ssl_keyfile": str(key_path)}
            scheme = "https"
        except Exception as exc:
            print(f"HTTPS unavailable ({exc}). Install: pip install cryptography")
            print("Falling back to HTTP — iPhone camera will not work.")
            scheme = "http"
    else:
        scheme = "http"

    ip = local_lan_ip()
    print(f"Arm twin v{API_VERSION} — motor control at /api/start, /api/stop, /api/settings")
    print(f"PC:    {scheme}://localhost:8000")
    if ip:
        print(f"Phone: {scheme}://{ip}:8000/wrist-camera")
    if scheme == "https":
        print("iPhone: open the Phone URL in Safari, tap Advanced, Continue if warned about certificate")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False, **ssl_kwargs)
