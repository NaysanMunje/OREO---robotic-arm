# Fusion — do these steps in order (your arm)

Do **one phase at a time**. Do not export until Phase 4 passes.

Your motors: **M4** = base spin, **M2** = shoulder, **M3** = elbow.  
Ignore wrist **M1** for now.

---

## Phase 0 — Backup (2 minutes)

1. Open your arm design in Fusion.
2. **File → Save As** → name it `arm_urdf_backup.f3d`.
3. Keep working in that copy.

---

## Phase 1 — Make exactly 4 components

You need **4 names** in the Browser (left panel). Nothing else at the top level except these (plus Joints later).

### Names you will use

| # | Browser name      | Physical part |
|---|-------------------|---------------|
| 1 | `base_link`       | Plate screwed to table — **does not move** |
| 2 | `link_shoulder`   | Turntable + housing — moves when **M4** turns |
| 3 | `link_upper_arm`  | Upper arm — moves when **M2** turns |
| 4 | `link_forearm`    | Forearm + gripper — moves when **M3** turns |

### 1.1 — Find your solids

1. Left **Browser** → expand the top assembly (top line).
2. You will see **Bodies** and/or **Components** (maybe `Body1`, `Body2`, `Body38`, etc.).

### 1.2 — Create `base_link`

1. Click the **table plate** body only (the part that stays on the desk).
2. Right-click that body → **Create Components from Bodies** (or **New Component** then drag body in).
3. Slow double-click the new component name → type **`base_link`** → Enter.

### 1.3 — Create `link_shoulder`

1. Select every solid that **spins with the base motor (M4)** but is **not** the table plate.
   - Turntable, base gearbox, vertical post up to the shoulder axis.
2. Right-click → **Create Components from Bodies** (one component for all of them together).
3. Rename component → **`link_shoulder`**.

### 1.4 — Create `link_upper_arm`

1. Select solids from **shoulder axis → elbow axis** (the 187 mm upper section).
2. New component from those bodies.
3. Rename → **`link_upper_arm`**.

### 1.5 — Create `link_forearm`

1. Select everything from **elbow → gripper tip**.
2. New component.
3. Rename → **`link_forearm`**.

### 1.6 — Check Browser looks like this

```
▼ (root assembly name)
   ▶ base_link
   ▶ link_shoulder
   ▶ link_upper_arm
   ▶ link_forearm
```

**Not OK:** `Body1`, `Body38` still at the top level. Move those bodies into the 4 components above.

**Not OK:** A component inside another component (for first export). Each of the 4 should contain **bodies only**.

---

## Phase 2 — Ground the base (1 minute)

1. Right-click **`base_link`** in the Browser.
2. Click **Ground** (you should see a pin icon on `base_link`).
3. Confirm **`link_shoulder`**, **`link_upper_arm`**, **`link_forearm`** are **not** grounded.

---

## Phase 3 — Add 3 joints (Revolute)

Open: top menu **Assemble** → **Assemble** → **Joint**.

For each joint you will:
- Click once on the **parent** part (closer to table).
- Click once on the **child** part (further from table).
- Choose **Revolute**.
- Set min/max angle.
- Type the **joint name** exactly as written below.

---

### Joint A — base (motor M4)

| Field | What to pick / type |
|-------|---------------------|
| First click | Any flat face or edge on **`base_link`** |
| Second click | Any face or edge on **`link_shoulder`** |
| Type | **Revolute** |
| Axis | Use **Flip** until the arrow is along the **vertical** spin axis of the base |
| Motion → Minimum | `0 deg` |
| Motion → Maximum | `130 deg` |
| Name (in joint settings) | **`joint_base`** |
| Finish | **OK** |

---

### Joint B — shoulder (motor M2)

| Field | What to pick / type |
|-------|---------------------|
| First click | Face/edge on **`link_shoulder`** |
| Second click | Face/edge on **`link_upper_arm`** |
| Type | **Revolute** |
| Axis | Flip until arrow is along the **shoulder hinge pin** |
| Minimum | `0 deg` |
| Maximum | `130 deg` |
| Name | **`joint_shoulder`** |
| Finish | **OK** |

---

### Joint C — elbow (motor M3)

| Field | What to pick / type |
|-------|---------------------|
| First click | Face/edge on **`link_upper_arm`** |
| Second click | Face/edge on **`link_forearm`** |
| Type | **Revolute** |
| Axis | Flip until arrow is along the **elbow pin** |
| Minimum | `0 deg` |
| Maximum | `200 deg` |
| Name | **`joint_elbow`** |
| Finish | **OK** |

---

## Phase 4 — Test in Fusion (must pass)

1. Browser → expand **Joints** (folder near bottom of tree).
2. You must see exactly: `joint_base`, `joint_shoulder`, `joint_elbow`.
3. Right-click **`joint_base`** → **Animate Joint** (or **Drive Joint**).
   - Drag slider: **only** `link_shoulder`, `link_upper_arm`, `link_forearm` move together; `base_link` stays fixed.
4. Reset. Animate **`joint_shoulder`**:
   - **Only** `link_upper_arm` and `link_forearm` move; base and `link_shoulder` do not bend at the shoulder (except shoulder bracket is parent — upper arm swings).
5. Reset. Animate **`joint_elbow`**:
   - **Only** `link_forearm` moves.

**If the wrong chunk moves:** stop. A body is in the wrong component. Go back to Phase 1 and move bodies.

---

## Phase 5 — Export URDF

### 5.1 — Install exporter (once per PC)

1. Download: https://github.com/syuntoku14/fusion2urdf (green **Code → Download ZIP**).
2. Unzip somewhere (e.g. `Documents/fusion2urdf`).
3. Fusion → **Utilities** (wrench) → **Add-Ins** → **Scripts and Add-Ins**.
4. Tab **Add-Ins** → green **+** → select the unzipped folder → **Open**.
5. Check the box next to the URDF exporter to enable it.

### 5.2 — Export

1. **File → Save** your Fusion file.
2. Right-click **`base_link`** → **Unground** (required for export).
3. **Add-Ins** panel → run **URDF Exporter** (exact name depends on add-in).
4. Choose folder (e.g. Desktop `arm_export`) → wait until finished.
5. In that folder you should see **`*.urdf`** and a **`meshes`** folder with **`.stl`** files.

### 5.3 — Copy to project

Copy into:

```
arm_twin/models/arm/
  robot.urdf
  meshes/   (all .stl files)
```

### 5.4 — Tell the viewer the joint names

Open `robot.urdf` in Notepad. Confirm you see:

```xml
<joint name="joint_base" type="revolute">
<joint name="joint_shoulder" type="revolute">
<joint name="joint_elbow" type="revolute">
```

`model_viewer/model_config.json` already uses those names. Open **http://localhost:8010** and reload.

---

## If you get stuck

| Symptom | What to do |
|---------|------------|
| Can't find "Create Components from Bodies" | Select body first, then right-click in Browser |
| Joint command won't pick second part | Hold Shift, click parent then child |
| Whole arm moves on every joint | Bodies not split — redo Phase 1 |
| Exporter crashes / no file | Rename base to `base_link`, unground, flatten nested components |
| Viewer empty | Copy `meshes` folder; check files are under `arm_twin/models/arm/` |

When Phase 4 works in Fusion, URDF will work. Fusion is the hard part; export is automatic after that.
