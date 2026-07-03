# EccentricLobeGearGenerator — Fusion 360 Add-In
# Meshing helical lobe gears with eccentric center distance.

import adsk.core
import adsk.fusion
import traceback
import math

CMD_ID = 'EccentricLobeGearGeneratorCommand'
CMD_NAME = 'Eccentric Lobe Gears'
CMD_DESC = 'Generate eccentric helical lobe gear pair'
# 4th arg to addButtonDefinition is the resources folder name (not tooltip)
RESOURCE_FOLDER = 'resources'

MM = 0.1  # Fusion internal units: cm
ADDIN_VERSION = '1.2.0'

handlers = []
command_definition = None
command_control = None


# ---------------------------------------------------------------------------
# Gear geometry
# ---------------------------------------------------------------------------

def _lobe_radius(theta, pitch_radius, lobe_depth, lobe_count, sharpness):
    wave = 0.5 * (1.0 + math.cos(lobe_count * theta))
    wave = wave ** sharpness
    return pitch_radius + lobe_depth * wave


def _profile_points(pitch_radius, lobe_depth, lobe_count, sharpness, points_per_lobe=24):
    pts = []
    total = max(int(lobe_count) * points_per_lobe, 120)
    for i in range(total):
        theta = (2.0 * math.pi * i) / total
        r = _lobe_radius(theta, pitch_radius, lobe_depth, lobe_count, sharpness)
        pts.append((r * math.cos(theta), r * math.sin(theta)))
    return pts


def _add_closed_profile(sketch, points):
    lines = sketch.sketchCurves.sketchLines
    splines = sketch.sketchCurves.sketchFittedSplines
    fit_pts = adsk.core.ObjectCollection.create()

    for x, y in points:
        fit_pts.add(adsk.core.Point3D.create(x * MM, y * MM, 0))

    x0, y0 = points[0]
    fit_pts.add(adsk.core.Point3D.create(x0 * MM, y0 * MM, 0))
    spline = splines.add(fit_pts)

    if spline.startSketchPoint.geometry.distanceTo(spline.endSketchPoint.geometry) > 1e-6:
        lines.addByTwoPoints(spline.endSketchPoint, spline.startSketchPoint)

    return spline


def _largest_profile(sketch):
    best = None
    best_area = -1.0
    for i in range(sketch.profiles.count):
        prof = sketch.profiles.item(i)
        bbox = prof.boundingBox
        area = (bbox.maxPoint.x - bbox.minPoint.x) * (bbox.maxPoint.y - bbox.minPoint.y)
        if area > best_area:
            best_area = area
            best = prof
    return best


def _loft_profile(sketch, bore_mm):
    """Return ring profile when bored, otherwise the outer closed profile."""
    if bore_mm > 0:
        for i in range(sketch.profiles.count):
            prof = sketch.profiles.item(i)
            if prof.profileLoops.count == 2:
                return prof
        raise RuntimeError('Could not find ring profile for bored loft sketch')
    return _largest_profile(sketch)


def _add_bore_circle(sketch, bore_mm):
    if bore_mm > 0:
        sketch.sketchCurves.sketchCircles.addByCenterRadius(
            adsk.core.Point3D.create(0, 0, 0),
            (bore_mm * 0.5) * MM,
        )


def _extrude_new_body(extrudes, profile, distance_mm):
    """Use ExtrudeFeatures.addSimple — stable across current Fusion API builds."""
    distance = adsk.core.ValueInput.createByString('{} mm'.format(distance_mm))
    return extrudes.addSimple(
        profile,
        distance,
        adsk.fusion.FeatureOperations.NewBodyFeatureOperation,
    )


def _move_body(move_features, body, transform):
    """MoveFeatures.add() now requires MoveFeatureInput, not (body, transform)."""
    bodies = adsk.core.ObjectCollection.create()
    bodies.add(body)
    move_input = move_features.createInput(bodies, transform)
    return move_features.add(move_input)


def _create_helical_loft_body(comp, points, height_mm, twist_deg, bore_mm, body_name):
    sketches = comp.sketches
    xy = comp.xYConstructionPlane
    planes = comp.constructionPlanes

    sk_bot = sketches.add(xy)
    sk_bot.name = body_name + '_bottom'
    _add_closed_profile(sk_bot, points)
    _add_bore_circle(sk_bot, bore_mm)
    bot_prof = _loft_profile(sk_bot, bore_mm)
    if not bot_prof:
        raise RuntimeError('Could not build bottom profile for ' + body_name)

    plane_input = planes.createInput()
    plane_input.setByOffset(xy, adsk.core.ValueInput.createByReal(height_mm * MM))
    top_plane = planes.add(plane_input)
    top_plane.name = body_name + '_top_plane'

    sk_top = sketches.add(top_plane)
    sk_top.name = body_name + '_top'

    twist_rad = math.radians(twist_deg)
    top_pts = []
    for x, y in points:
        xr = x * math.cos(twist_rad) - y * math.sin(twist_rad)
        yr = x * math.sin(twist_rad) + y * math.cos(twist_rad)
        top_pts.append((xr, yr))

    _add_closed_profile(sk_top, top_pts)
    _add_bore_circle(sk_top, bore_mm)
    top_prof = _loft_profile(sk_top, bore_mm)
    if not top_prof:
        raise RuntimeError('Could not build top profile for ' + body_name)

    lofts = comp.features.loftFeatures
    loft_input = lofts.createInput(adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    loft_input.loftSections.add(bot_prof)
    loft_input.loftSections.add(top_prof)
    loft_input.isSolid = True
    loft = lofts.add(loft_input)
    loft.name = body_name

    if loft.bodies.count > 0:
        return loft.bodies.item(0)
    return None


def _mm_value(inputs, input_id):
    """Read a ValueCommandInput shown in mm; Fusion stores lengths internally as cm."""
    inp = adsk.core.ValueCommandInput.cast(inputs.itemById(input_id))
    return inp.value * 10.0


def _real_value(inputs, input_id):
    inp = adsk.core.ValueCommandInput.cast(inputs.itemById(input_id))
    return inp.value


def _params_from_inputs(inputs):
    return {
        'main_lobes': inputs.itemById('main_lobes').value,
        'driver_lobes': inputs.itemById('driver_lobes').value,
        'main_pitch_radius': _mm_value(inputs, 'main_pitch_radius'),
        'driver_pitch_radius': _mm_value(inputs, 'driver_pitch_radius'),
        'main_lobe_depth': _mm_value(inputs, 'main_lobe_depth'),
        'driver_lobe_depth': _mm_value(inputs, 'driver_lobe_depth'),
        'tooth_sharpness': _real_value(inputs, 'tooth_sharpness'),
        'eccentric_offset': _mm_value(inputs, 'eccentric_offset'),
        'gear_height': _mm_value(inputs, 'gear_height'),
        'helix_twist_deg': _real_value(inputs, 'helix_twist_deg'),
        'main_bore': _mm_value(inputs, 'main_bore'),
        'driver_bore': _mm_value(inputs, 'driver_bore'),
        'driver_angle_deg': _real_value(inputs, 'driver_angle_deg'),
        'create_base_plate': 1 if inputs.itemById('create_base_plate').value else 0,
        'base_width': _mm_value(inputs, 'base_width'),
        'base_depth': _mm_value(inputs, 'base_depth'),
        'base_thickness': _mm_value(inputs, 'base_thickness'),
    }


def _add_command_inputs(inputs):
    """One Fusion input row per parameter."""
    inputs.addTextBoxCommandInput('hdr_main', '', 'Main gear', 1, True)

    inputs.addIntegerSpinnerCommandInput('main_lobes', 'Main lobe count', 1, 200, 1, 15)

    inputs.addValueInput(
        'main_pitch_radius', 'Main pitch radius', 'mm',
        adsk.core.ValueInput.createByString('40 mm'),
    )
    inputs.addValueInput(
        'main_lobe_depth', 'Main lobe depth', 'mm',
        adsk.core.ValueInput.createByString('6 mm'),
    )
    inputs.addValueInput(
        'main_bore', 'Main bore (0 = none)', 'mm',
        adsk.core.ValueInput.createByString('8 mm'),
    )

    inputs.addTextBoxCommandInput('hdr_driver', '', 'Driver gear', 1, True)

    inputs.addIntegerSpinnerCommandInput('driver_lobes', 'Driver lobe count', 1, 20, 1, 1)

    inputs.addValueInput(
        'driver_pitch_radius', 'Driver pitch radius', 'mm',
        adsk.core.ValueInput.createByString('12 mm'),
    )
    inputs.addValueInput(
        'driver_lobe_depth', 'Driver lobe depth', 'mm',
        adsk.core.ValueInput.createByString('5 mm'),
    )
    inputs.addValueInput(
        'driver_bore', 'Driver bore (0 = none)', 'mm',
        adsk.core.ValueInput.createByString('6 mm'),
    )
    inputs.addValueInput(
        'driver_angle_deg', 'Driver angle offset', 'deg',
        adsk.core.ValueInput.createByString('0 deg'),
    )

    inputs.addTextBoxCommandInput('hdr_layout', '', 'Layout and helix', 1, True)

    inputs.addValueInput(
        'tooth_sharpness', 'Tooth roundness (>1 = rounder)', '',
        adsk.core.ValueInput.createByString('1.6'),
    )
    inputs.addValueInput(
        'eccentric_offset', 'Eccentric center distance', 'mm',
        adsk.core.ValueInput.createByString('50 mm'),
    )
    inputs.addValueInput(
        'gear_height', 'Gear height', 'mm',
        adsk.core.ValueInput.createByString('25 mm'),
    )
    inputs.addValueInput(
        'helix_twist_deg', 'Helix twist over height', 'deg',
        adsk.core.ValueInput.createByString('17 deg'),
    )

    inputs.addTextBoxCommandInput('hdr_base', '', 'Base plate', 1, True)

    create_base = inputs.addBoolValueInput('create_base_plate', 'Create base plate', True, '', True)
    create_base.value = True

    inputs.addValueInput(
        'base_width', 'Base width', 'mm',
        adsk.core.ValueInput.createByString('140 mm'),
    )
    inputs.addValueInput(
        'base_depth', 'Base depth', 'mm',
        adsk.core.ValueInput.createByString('90 mm'),
    )
    inputs.addValueInput(
        'base_thickness', 'Base thickness', 'mm',
        adsk.core.ValueInput.createByString('6 mm'),
    )


def _get_gear_component(design):
    """Part (.f3d) files allow only one component — build in root. Assemblies can use a child."""
    root = design.rootComponent
    try:
        gear_occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        gear_comp = gear_occ.component
        gear_comp.name = 'EccentricLobeGearSet'
        return gear_comp, 'assembly'
    except RuntimeError:
        return root, 'part'


def _build_gear_set(ui, params):
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    if not design:
        ui.messageBox('Open a Fusion design (not a drawing) before running this add-in.')
        return

    gear_comp, doc_mode = _get_gear_component(design)

    main_pts = _profile_points(
        params['main_pitch_radius'], params['main_lobe_depth'],
        int(params['main_lobes']), params['tooth_sharpness'],
    )
    driver_pts = _profile_points(
        params['driver_pitch_radius'], params['driver_lobe_depth'],
        max(1, int(params['driver_lobes'])), params['tooth_sharpness'],
    )

    _create_helical_loft_body(
        gear_comp, main_pts, params['gear_height'], params['helix_twist_deg'],
        params['main_bore'], 'MainLobeGear',
    )

    driver_body = _create_helical_loft_body(
        gear_comp, driver_pts, params['gear_height'], params['helix_twist_deg'],
        params['driver_bore'], 'DriverLobeGear',
    )

    if driver_body:
        move_feats = gear_comp.features.moveFeatures
        ang = math.radians(params['driver_angle_deg'])
        tx = params['eccentric_offset'] * math.cos(ang) * MM
        ty = params['eccentric_offset'] * math.sin(ang) * MM
        transform = adsk.core.Matrix3D.create()
        transform.translation = adsk.core.Vector3D.create(tx, ty, 0)
        _move_body(move_feats, driver_body, transform)

    if int(params['create_base_plate']) == 1:
        sketches = gear_comp.sketches
        xy = gear_comp.xYConstructionPlane
        sk = sketches.add(xy)
        sk.name = 'BasePlateSketch'
        lines = sk.sketchCurves.sketchLines
        half_w = params['base_width'] * MM * 0.5
        half_d = params['base_depth'] * MM * 0.5
        p1 = adsk.core.Point3D.create(-half_w, -half_d, 0)
        p2 = adsk.core.Point3D.create(half_w, -half_d, 0)
        p3 = adsk.core.Point3D.create(half_w, half_d, 0)
        p4 = adsk.core.Point3D.create(-half_w, half_d, 0)
        lines.addByTwoPoints(p1, p2)
        lines.addByTwoPoints(p2, p3)
        lines.addByTwoPoints(p3, p4)
        lines.addByTwoPoints(p4, p1)
        prof = sk.profiles.item(0)
        extrudes = gear_comp.features.extrudeFeatures
        _extrude_new_body(extrudes, prof, -params['base_thickness']).name = 'BasePlate'

    ratio = int(params['main_lobes']) / max(1, int(params['driver_lobes']))
    where = (
        'Bodies added to the root component (Part Design allows only one component).'
        if doc_mode == 'part'
        else 'Created in EccentricLobeGearSet sub-component.'
    )
    ui.messageBox(
        'Gear set created (add-in v{}).\n'
        '{}\n'
        'Nominal ratio hint: {:.1f}:1\n'
        'Tune eccentric offset and lobe depth for mesh.'.format(ADDIN_VERSION, where, ratio)
    )


# ---------------------------------------------------------------------------
# Fusion command handlers (required for add-in)
# ---------------------------------------------------------------------------

class CommandExecuteHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        try:
            app = adsk.core.Application.get()
            ui = app.userInterface
            params = _params_from_inputs(args.command.commandInputs)
            _build_gear_set(ui, params)
        except Exception:
            app = adsk.core.Application.get()
            ui = app.userInterface
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


class CommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        try:
            cmd = args.command
            cmd.isRepeatable = False
            _add_command_inputs(cmd.commandInputs)

            on_execute = CommandExecuteHandler()
            cmd.execute.add(on_execute)
            handlers.append(on_execute)
        except Exception:
            app = adsk.core.Application.get()
            ui = app.userInterface
            ui.messageBox('Command setup failed:\n{}'.format(traceback.format_exc()))


def _get_addins_panel(ui):
    workspace = ui.workspaces.itemById('FusionSolidEnvironment')
    if not workspace:
        return None
    return workspace.toolbarPanels.itemById('SolidScriptsAddinsPanel')


def run(context):
    global command_definition, command_control

    try:
        app = adsk.core.Application.get()
        ui = app.userInterface

        cmd_defs = ui.commandDefinitions
        command_definition = cmd_defs.itemById(CMD_ID)
        if not command_definition:
            command_definition = cmd_defs.addButtonDefinition(
                CMD_ID, CMD_NAME, CMD_DESC, RESOURCE_FOLDER
            )
            command_definition.toolClipFilename = RESOURCE_FOLDER + '/tooltip.html'

        on_created = CommandCreatedHandler()
        command_definition.commandCreated.add(on_created)
        handlers.append(on_created)

        panel = _get_addins_panel(ui)
        if panel:
            command_control = panel.controls.itemById(CMD_ID)
            if not command_control:
                command_control = panel.controls.addCommand(command_definition)
                command_control.isPromotedByDefault = True
                command_control.isPromoted = True

    except Exception:
        app = adsk.core.Application.get()
        ui = app.userInterface
        ui.messageBox('Add-in failed to start:\n{}'.format(traceback.format_exc()))


def stop(context):
    global command_definition, command_control

    try:
        app = adsk.core.Application.get()
        ui = app.userInterface

        panel = _get_addins_panel(ui)
        if panel:
            command_control = panel.controls.itemById(CMD_ID)
            if command_control:
                command_control.deleteMe()

        command_definition = ui.commandDefinitions.itemById(CMD_ID)
        if command_definition:
            command_definition.deleteMe()

    except Exception:
        app = adsk.core.Application.get()
        ui = app.userInterface
        ui.messageBox('Add-in failed to stop:\n{}'.format(traceback.format_exc()))
