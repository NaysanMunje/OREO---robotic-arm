# Fusion 360 → Digital Twin

Fusion does **not** include GLB in the default export menu. Use **FBX** (built-in) or optional add-ins below.

**Wrist (M1) is skipped for now** — only 3 joints: base, shoulder, elbow.

## 1. Components in Fusion

Create **three** pivot components (names must match exactly):

| Component name | Motor | Role |
|----------------|-------|------|
| `joint_m4` | M4 | Base |
| `joint_m2` | M2 | Shoulder |
| `joint_m3` | M3 | Elbow |

Put wrist/gripper geometry **inside `joint_m3`** as fixed mesh (no extra joint) until you add M1 later.

**Hierarchy:**

```
joint_m4
  └── joint_m2
        └── joint_m3   ← include forearm + wrist + gripper solids here
```

- Component **origin** = real hinge axis.
- Rename in the Fusion **Browser** (slow double-click).

## 2. Export FBX (recommended)

1. Select the **top-level assembly** in the Browser.
2. **File → Export** (or right-click root → Export).
3. Choose **FBX** (`.fbx`).
4. Save as:

   `arm_twin/models/arm.fbx`

## 3. Enable in config

Edit `arm_twin/config.json`:

```json
"model": "fbx",
"model_file": "models/arm.fbx"
```

## 4. Run twin

```powershell
cd arm_twin
.\.venv\Scripts\Activate.ps1
python main.py
```

PC on **`ESP32-Arm`** WiFi → **http://localhost:8000**

Check **3D model** panel: should say **3/3 joints matched**.

Press **F12 → Console** if names are wrong — lists every node name in the FBX.

## 5. Tune

In `config.json` per joint:

- `axis` — `"x"`, `"y"`, or `"z"`
- `sign` — `-1` if rotation is backwards vs real arm
- `model_scale` — e.g. `0.1` if model is huge/tiny (Fusion often exports in cm)
- `model_rotation_deg` — e.g. `[90, 0, 0]` if model lies on its side

## Other export options

### GLB via add-in (optional)

1. [Autodesk App Store](https://apps.autodesk.com) → search **glTF** or **GLB**
2. Install **glTF Exporter** for Fusion 360
3. Export `.glb` → set `"model": "glb"` and `"model_file": "models/arm.glb"`

### GLB via Blender (free)

1. Fusion → Export **STEP** (`.step`)
2. Blender → File → Import → STEP (may need CAD Sketcher / STEP import add-on)
3. Fix hierarchy / names if needed
4. File → Export → **glTF 2.0 (.glb)**

### STL (not recommended)

STL has **no component names** — joints won’t work. Use FBX or GLB instead.

## Checklist

- [ ] `joint_m4`, `joint_m2`, `joint_m3` named and nested correctly
- [ ] Wrist geometry parented under `joint_m3` (fixed, no M1 joint)
- [ ] `arm.fbx` in `arm_twin/models/`
- [ ] `"model": "fbx"` in config.json
- [ ] Twin shows 3/3 joints matched
- [ ] Sliders move correct links in 3D

## Add wrist later

1. Add component `joint_m1` under `joint_m3`
2. Move wrist/gripper solids under `joint_m1`
3. Re-export FBX
4. Add M1 entry back to `config.json` `joints` array
