# Fusion 360 Add-In: Eccentric Lobe Gear Generator

Proper Fusion **add-in** package (not a loose script file).

## Why the old file did not show up

Fusion **Add-Ins** require all of this:

1. A **folder** named `EccentricLobeGearGenerator`
2. A **`.py` file** with the **same name** as the folder
3. A **`.manifest` file** with the **same name** as the folder
4. The folder copied into Fusion's **AddIns** directory

A single `.py` file in your project folder cannot be added from the Add-Ins tab.

## Reload after updates (important)

Fusion **caches** add-in Python until you restart it:

1. **Utilities → Scripts and Add-Ins → Add-Ins**
2. Select **EccentricLobeGearGenerator**
3. Click **Stop**, then **Run**
4. Success message should say **add-in v1.2.0**

If errors persist, restart Fusion 360 completely.

## Install (recommended)

In PowerShell:

```powershell
cd fusion360
.\install-addin.ps1
```

Then in Fusion 360:

1. **Utilities → Scripts and Add-Ins**
2. Open the **Add-Ins** tab
3. Find **EccentricLobeGearGenerator**
4. Enable **Run on Startup** (or click **Run** once)
5. Go to **SOLID** workspace → **ADD-INS** toolbar → click **Eccentric Lobe Gears**

## Manual install

Copy this entire folder:

```
fusion360\EccentricLobeGearGenerator\
```

To:

```
%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\EccentricLobeGearGenerator\
```

Must contain:

```
EccentricLobeGearGenerator/
  EccentricLobeGearGenerator.py
  EccentricLobeGearGenerator.manifest
```

## Package layout

| File | Purpose |
|------|---------|
| `EccentricLobeGearGenerator.manifest` | Fusion add-in metadata (required) |
| `EccentricLobeGearGenerator.py` | `run()` / `stop()` + toolbar command |
| `install-addin.ps1` | Copies package to Fusion AddIns folder |

## Default parameters

- 15-lobe main gear, 1-lobe driver
- 40 mm / 12 mm pitch radius
- 17° helix twist over 25 mm height
- Eccentric offset 50 mm

## Notes

- Creates **meshing lobe gears**, not pin-housing cycloidal reducers.
- Open a **design** (`.f3d`), not a drawing, before running.
- After install, restart Fusion if the add-in does not appear immediately.
