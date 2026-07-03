"""CAD model validation tests (standalone model viewer)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

VIEWER_ROOT = Path(__file__).resolve().parents[1] / "model_viewer"
sys.path.insert(0, str(VIEWER_ROOT))

from main import _find_name_in_fbx, _validate_joint_names, model_test_report  # noqa: E402

CONFIG_PATH = VIEWER_ROOT / "model_config.json"


def test_find_name_exact_and_fuzzy() -> None:
    names = ["Body1", "Body2", "joint_m4", "SomePart:1"]
    assert _find_name_in_fbx(names, ["Body1"]) == "Body1"
    assert _find_name_in_fbx(names, ["body2"]) == "Body2"
    assert _find_name_in_fbx(names, ["m4"]) == "joint_m4"
    assert _find_name_in_fbx(names, ["missing"]) is None


def test_validate_joint_names_partial() -> None:
    cfg = {
        "joints": [
            {"label": "M4", "node": "Body1"},
            {"label": "M2", "node": "Body99"},
        ]
    }
    checks = _validate_joint_names(cfg, ["Body1", "Body2"])
    assert checks[0]["ok"] is True
    assert checks[1]["ok"] is False


def test_model_test_report_structure() -> None:
    report = model_test_report()
    assert report["model"] == "fbx"
    assert "checks" in report
    assert "summary" in report
