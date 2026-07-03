# Fusion 360 → URDF (detailed guide for your arm)

This guide is for your **3-joint arm** (M4 base, M2 shoulder, M3 elbow). Wrist M1 can be added later.

URDF exports **Fusion assembly joints** (axis + limits + parent/child). It does **not** use FBX-style `Body1` / `Body2` names.

---

## What you are building in Fusion

Think in **links** (rigid chunks) and **joints** (hinges between them):

```
base_link          ← fixed to table; does NOT rotate (grounded)
  │
  │  joint_base (revolute) ← M4 motor: whole arm spins on base
  ▼
link_shoulder      ← turntable + shoulder bracket (everything above base)
  │
  │  joint_shoulder (revolute) ← M2 motor
  ▼
link_upper_arm     ← upper arm tube / gearbox to elbow
  │
  │  joint_elbow (revolute) ← M3 motor
  ▼
link_forearm       ← forearm + wrist + gripper (fixed together for now)
```

**Rule:** Everything that must move **together** belongs in the **same component**.  
**Rule:** Each **revolute joint** allows **one** degree of freedom between two components.

---

## Before you start

1. **Save a copy** of your Fusion file (e.g. `arm_for_urdf.f3d`). Exporters can change the assembly.
2. Work in the **Design** workspace (not Manufacture).
3. Use **mm** as document units (matches your measurements).

---

## Step 1 — Split geometry into components (links)

You probably have one big component or bodies named `Body1`, `Body2`, `Body38`. URDF needs **named link components**.

### 1a. Create link components

For each moving chunk, you want a **component** in the Browser:

| Component name   | Real part                         | Motor |
|------------------|-----------------------------------|-------|
| `base_link`      | Plate bolted to table (optional)  | —     |
| `link_shoulder`  | Base rotation + shoulder housing    | M4    |
| `link_upper_arm` | Upper arm (shoulder → elbow)      | M2    |
| `link_forearm`   | Forearm, wrist, gripper           | M3    |

**How to create a component from a body:**

1. In the Browser, expand your assembly.
2. Right-click a **body** (solid) → **Create components from bodies**.
   - Or: select bodies → right-click → **Create component** / move into new component.
3. Slow double-click the component name → rename (e.g. `link_upper_arm`).

### 1b. What goes where

- **Table/floor plate** → `base_link` only (stays fixed).
- **Everything that rotates when M4 turns** → inside `link_shoulder` (or split further if you prefer).
- **Everything that rotates when M2 turns** (but not when only M4 turns) → `link_upper_arm`.
- **Everything that rotates when M3 turns** → `link_forearm`.

If unsure: imagine moving **only one motor** at a time. All solids that move together go in one link.

### 1c. Avoid nested components (for classic fusion2urdf)

The older **fusion2urdf** script wants:

- Each link component contains **bodies only**
- **No component inside another component**

If you have nested folders, either flatten (move bodies up) or use the newer **[fusion2URDF](https://github.com/Adriaeik/fusion2URDF)** add-in which supports nesting.

---

## Step 2 — Set component origins (joint axes)

Each hinge needs a correct **origin** (axis location + direction).

### 2a. Activate the child link component

1. In Browser, find `link_upper_arm` (example).
2. Right-click → **Activate** (or double-click the component).
3. You are now editing **inside** that component.

### 2b. Move the origin to the hinge

1. **Construct** → **Offset Plane** or use existing geometry at the hinge center.
2. **Modify** → **Move/Copy** → select **Origin** (or use **Reorient Z Axis** / **Set Pivot** depending on Fusion version).
3. Place the component origin on the **real rotation axis** (center of the motor shaft / pin).

Repeat for each link so that when the joint rotates, the part spins around the correct line.

**Tips:**

- **M4 base:** vertical axis through center of turntable (often Fusion **Z** when arm stands on table).
- **M2 shoulder:** axis through shoulder pin (often horizontal).
- **M3 elbow:** axis through elbow pin.

Exact axis direction is corrected later in the viewer with `sign` if needed; **position** matters most here.

### 2c. Return to top level

Click the **root** component (top of Browser tree) to exit isolation.

---

## Step 3 — Ground the base

1. Right-click **`base_link`** → **Ground** (pin icon appears).
2. Only **`base_link`** should be grounded. Child links must **not** be grounded.

You will **unground** before URDF export (exporter requirement).

---

## Step 4 — Create revolute joints in Fusion

This is the step that replaces “constraints” in the digital twin.

### 4a. Open Joint command

1. **Assemble** tab → **Assemble** → **Joint** (or **Rigid** / **Revolute** joint tool).

### 4b. Base joint (M4) — `joint_base`

1. **First selection (Component 1):** click geometry on **`base_link`** (fixed parent).
2. **Second selection (Component 2):** click geometry on **`link_shoulder`** (child that rotates).
   - **Important for fusion2urdf:** parent link should be **Component 2** in the joint dialog when the exporter docs say so — if export fails, swap and try again.
3. Joint type: **Revolute**.
4. Align the axis (flip with **Flip** if arrow points wrong way).
5. **Motion** tab / limits:
   - **Minimum:** `0 deg` (or your limit-switch home)
   - **Maximum:** `130 deg` (your measured max)
6. Name the joint: **`joint_base`** (remember this name for `model_config.json`).
7. Click **OK**.

### 4c. Shoulder joint (M2) — `joint_shoulder`

1. Component 1: `link_shoulder` (parent — closer to base).
2. Component 2: `link_upper_arm` (child).
3. Type: **Revolute**.
4. Axis: through shoulder hinge.
5. Limits: `0` → `130` deg (match your arm).
6. Name: **`joint_shoulder`**.

### 4d. Elbow joint (M3) — `joint_elbow`

1. Component 1: `link_upper_arm`.
2. Component 2: `link_forearm`.
3. Type: **Revolute**.
4. Limits: `0` → `200` deg.
5. Name: **`joint_elbow`**.

### 4e. Check joints

1. Browser → **Joints** folder — you should see 3 revolute joints.
2. Right-click a joint → **Animate joint** / drag slider — **only the correct parts** should move.
3. If the wrong chunk moves, your components are split wrong → go back to Step 1.

---

## Step 5 — Rigid joints for bolts (optional)

Screws, covers, and brackets that never move relative to a link:

- Use **Rigid** joint to parent them to the same link, **or**
- Simply model them **inside** the same component (no extra joint).

Do **not** add extra revolute joints unless they are real motors.

---

## Step 6 — Install URDF exporter add-in

1. Download one add-in (zip) from GitHub:
   - [fusion2urdf](https://github.com/syuntoku14/fusion2urdf) — simplest
   - [fusion2urdf-ros2](https://github.com/dheena2k2/fusion2urdf-ros2)
   - [fusion2URDF](https://github.com/Adriaeik/fusion2URDF) — if you need nested assemblies
2. Fusion → **Utilities** → **Add-Ins** (wrench icon) → **Scripts and Add-Ins**.
3. **Add-Ins** tab → green **+** → select the add-in folder → **Open**.
4. Enable the add-in (checkbox).

---

## Step 7 — Export URDF

1. **Back up** your `.f3d` again.
2. Right-click **`base_link`** → **Unground** (required before export).
3. Run the exporter from **Add-Ins** panel (name varies: “URDF Exporter”, etc.).
4. Choose output folder (e.g. Desktop `arm_urdf_export`).
5. Wait for meshes + `.urdf` to be generated.

### Copy into this project

Copy the whole export into:

```
arm_twin/models/arm/
  robot.urdf
  meshes/
    base_link.stl
    link_shoulder.stl
    ...
```

If the file is named differently, either rename to `robot.urdf` or update `model_file` in `model_config.json`.

### Check the URDF file

Open `robot.urdf` in Notepad. You should see lines like:

```xml
<joint name="joint_base" type="revolute">
  <limit lower="0" upper="2.27" ... />
```

Note every `name="..."` on revolute joints. Radians in file → viewer converts to degrees on sliders.

If meshes use `package://robot_description/meshes/...`, set in `model_config.json`:

```json
"urdf_package": "robot_description",
"urdf_package_path": "models/arm"
```

---

## Step 8 — Configure model viewer

Edit `arm_twin/model_viewer/model_config.json`:

```json
"urdf_joint": "joint_base"
```

must **exactly match** the `name` in the URDF `<joint>` tag (for M4, M2, M3).

Open **http://localhost:8010** → checklist green → drag sliders.

---

## Mapping to your real motors

| Motor | Fusion joint name (you choose) | Config label |
|-------|-------------------------------|--------------|
| M4 base | `joint_base` | M4 |
| M2 shoulder | `joint_shoulder` | M2 |
| M3 elbow | `joint_elbow` | M3 |
| M1 wrist | add later | — |

Use the **same names** in Fusion when you create joints so export is predictable.

---

## Common mistakes

| Problem | Cause | Fix |
|---------|--------|-----|
| Wrong part rotates in Fusion Animate | Bodies in wrong component | Reassign bodies to links (Step 1) |
| Wrong part rotates in viewer | Wrong `urdf_joint` name in config | Match URDF `<joint name>` |
| Exporter error `base_link` | No component named `base_link` | Rename grounded component |
| Exporter error nested components | Component inside component | Flatten or use fusion2URDF |
| Model invisible in viewer | Mesh paths wrong | Fix `urdf_package` / copy `meshes/` folder |
| Arm lies on side | ROS Z-up vs Three.js | `"ros_z_up": true` in config (default) |
| Joint spins backward | Axis flipped | `"sign": -1` on that joint in config |
| Limits wrong | Fusion joint limits not set | Set min/max in Joint dialog (Step 4) |

---

## Checklist before export

- [ ] Components: `base_link`, `link_shoulder`, `link_upper_arm`, `link_forearm`
- [ ] Origins on real hinge axes
- [ ] Only `base_link` grounded (then unground for export)
- [ ] 3 revolute joints named `joint_base`, `joint_shoulder`, `joint_elbow`
- [ ] Animate each joint in Fusion — correct parts move
- [ ] Limits set (0–130°, 0–130°, 0–200° or your values)
- [ ] URDF + `meshes/` copied to `arm_twin/models/arm/`
- [ ] `model_config.json` `urdf_joint` names match URDF file
- [ ] Test at http://localhost:8010

---

## After URDF works

When the model viewer looks correct, we can copy joint names into the ESP twin (`config.json`) — only when you want the real arm to follow the 3D model.
