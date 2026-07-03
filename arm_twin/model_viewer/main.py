"""Standalone Fusion/FBX/URDF model viewer — no ESP32, separate from arm twin."""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

VIEWER_ROOT = Path(__file__).resolve().parent
ARM_TWIN_ROOT = VIEWER_ROOT.parent
CONFIG_PATH = VIEWER_ROOT / "model_config.json"
PORT = 8010

app = FastAPI(title="Arm Model Viewer", version="1.0.0")
app.mount("/static", StaticFiles(directory=ARM_TWIN_ROOT / "static"), name="static")

models_dir = ARM_TWIN_ROOT / "models"
if models_dir.is_dir():
    app.mount("/models", StaticFiles(directory=models_dir), name="models")


def load_config() -> dict[str, Any]:
    with CONFIG_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def _find_name_in_fbx(names: list[str], candidates: list[str]) -> str | None:
    name_set = set(names)
    for candidate in candidates:
        if not candidate:
            continue
        if candidate in name_set:
            return candidate
        for n in names:
            if n.lower() == candidate.lower():
                return n
        low = candidate.lower()
        for n in names:
            if low in n.lower():
                return n
    return None


def _validate_joint_names(cfg: dict[str, Any], fbx_strings: list[str]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for j in cfg.get("joints", []):
        candidates = [j.get("node", "")] + list(j.get("node_candidates") or [])
        found = _find_name_in_fbx(fbx_strings, [c for c in candidates if c])
        checks.append(
            {
                "label": j.get("label"),
                "role": j.get("role"),
                "expected": j.get("node"),
                "found": found,
                "ok": found is not None,
            }
        )
    return checks


def _validate_urdf_joints(cfg: dict[str, Any], urdf_joint_names: list[str]) -> list[dict[str, Any]]:
    name_set = set(urdf_joint_names)
    checks: list[dict[str, Any]] = []
    for j in cfg.get("joints", []):
        candidates = [j.get("urdf_joint", "")] + list(j.get("urdf_joint_candidates") or [])
        candidates = [c for c in candidates if c]
        found = next((c for c in candidates if c in name_set), None)
        if not found:
            for c in candidates:
                for n in urdf_joint_names:
                    if c.lower() in n.lower():
                        found = n
                        break
                if found:
                    break
        checks.append(
            {
                "label": j.get("label"),
                "role": j.get("role"),
                "expected": j.get("urdf_joint") or candidates[0] if candidates else "?",
                "found": found,
                "ok": found is not None,
            }
        )
    return checks


def inspect_urdf_file(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"ok": False, "error": f"File not found: {path.name}"}
    root = ET.parse(path).getroot()
    if root.tag != "robot":
        return {"ok": False, "error": "Root element is not <robot>"}
    joints: list[dict[str, Any]] = []
    for j in root.findall("joint"):
        name = j.get("name", "")
        jtype = j.get("type", "")
        limit = j.find("limit")
        lower = upper = None
        if limit is not None:
            lower = limit.get("lower")
            upper = limit.get("upper")
        joints.append(
            {
                "name": name,
                "type": jtype,
                "lower_rad": float(lower) if lower is not None else None,
                "upper_rad": float(upper) if upper is not None else None,
            }
        )
    revolute = [j["name"] for j in joints if j["type"] in ("revolute", "continuous", "prismatic")]
    cfg = load_config()
    joint_checks = _validate_urdf_joints(cfg, revolute)
    return {
        "ok": True,
        "file": path.name,
        "robot_name": root.get("name"),
        "size_bytes": path.stat().st_size,
        "joints": joints,
        "revolute_joints": revolute,
        "joint_checks": joint_checks,
        "joints_matched": sum(1 for c in joint_checks if c["ok"]),
        "joints_total": len(joint_checks),
        "all_joints_matched": all(c["ok"] for c in joint_checks),
    }


def inspect_fbx_file(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"ok": False, "error": f"File not found: {path.name}"}
    data = path.read_bytes()
    strings = [
        s.decode("latin-1", errors="ignore")
        for s in re.findall(rb"[\x20-\x7e]{4,}", data)
    ]
    cfg = load_config()
    joint_checks = _validate_joint_names(cfg, strings)
    return {
        "ok": True,
        "file": path.name,
        "size_bytes": path.stat().st_size,
        "joint_checks": joint_checks,
        "joints_matched": sum(1 for c in joint_checks if c["ok"]),
        "joints_total": len(joint_checks),
        "all_joints_matched": all(c["ok"] for c in joint_checks),
        "all_node_names": sorted({s for s in strings if len(s) < 48 and not s.startswith("::")})[:200],
    }


def model_test_report() -> dict[str, Any]:
    cfg = load_config()
    model_kind = cfg.get("model", "fbx")
    rel = cfg.get("model_file", "models/arm.fbx")
    path = ARM_TWIN_ROOT / rel
    report: dict[str, Any] = {
        "model": model_kind,
        "model_file": rel,
        "config_file": "model_viewer/model_config.json",
        "file_exists": path.is_file(),
        "ready": False,
        "checks": [],
    }

    def add_check(name: str, ok: bool, detail: str) -> None:
        report["checks"].append({"name": name, "ok": ok, "detail": detail})

    add_check(
        "config_model_type",
        model_kind in ("fbx", "glb", "urdf"),
        f'model is "{model_kind}"',
    )
    add_check(
        "file_on_disk",
        path.is_file(),
        str(path) if path.is_file() else f"missing: {path}",
    )

    if not path.is_file():
        report["summary"] = "Export model to the path in model_config.json, then reload."
        return report

    if model_kind == "urdf":
        try:
            inspected = inspect_urdf_file(path)
        except ET.ParseError as exc:
            add_check("urdf_readable", False, str(exc))
            report["summary"] = f"Invalid URDF XML: {exc}"
            return report
        if not inspected.get("ok"):
            add_check("urdf_readable", False, inspected.get("error", "unknown"))
            report["summary"] = inspected.get("error", "URDF inspect failed")
            return report
        add_check("urdf_readable", True, f"{inspected['size_bytes']:,} bytes · robot {inspected.get('robot_name', '?')}")
        all_ok = inspected.get("all_joints_matched", False)
        add_check(
            "joint_names_in_urdf",
            all_ok,
            f"{inspected.get('joints_matched', 0)}/{inspected.get('joints_total', 0)} config joints found",
        )
        report["joint_checks"] = inspected.get("joint_checks", [])
        report["urdf_joints"] = inspected.get("revolute_joints", [])
        report["ready"] = all_ok
        report["summary"] = (
            "URDF OK — sliders use joint limits from file."
            if all_ok
            else "Map urdf_joint names in model_config.json — see urdf_joints in /api/model/test"
        )
        if not all_ok:
            report["summary"] += f" Available: {', '.join(inspected.get('revolute_joints', []))}"
        return report

    if model_kind == "fbx":
        inspected = inspect_fbx_file(path)
        if not inspected.get("ok"):
            add_check("fbx_readable", False, inspected.get("error", "unknown"))
            report["summary"] = inspected.get("error", "FBX inspect failed")
            return report
        add_check("fbx_readable", True, f"{inspected['size_bytes']:,} bytes")
        all_ok = inspected.get("all_joints_matched", False)
        add_check(
            "joint_names_in_fbx",
            all_ok,
            f"{inspected.get('joints_matched', 0)}/{inspected.get('joints_total', 0)} joints found in file",
        )
        report["joint_checks"] = inspected.get("joint_checks", [])
        report["ready"] = all_ok
        report["summary"] = (
            "Model OK — use sliders to verify rotation."
            if all_ok
            else "Fix joint names in model_viewer/model_config.json"
        )
        return report

    report["ready"] = True
    report["summary"] = "GLB present — use sliders to verify rotation."
    return report


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(VIEWER_ROOT / "static" / "index.html")


@app.get("/api/config")
async def get_config() -> dict[str, Any]:
    return load_config()


@app.get("/api/model/test")
async def model_test() -> dict[str, Any]:
    return model_test_report()


if __name__ == "__main__":
    import uvicorn

    print(f"Model viewer — no ESP32 · http://localhost:{PORT}")
    print(f"Config: {CONFIG_PATH}")
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")
