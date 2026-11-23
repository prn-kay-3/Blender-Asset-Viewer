"""
Simple Purple Frog - Blender script (works in Blender 3.x, 4.x and 5.x)

HOW TO USE
1. Open Blender, go to the "Scripting" workspace.
2. Click "New", paste this whole file, press "Run Script" (Alt+P).
3. Switch the 3D viewport to Material Preview (Z > Material Preview) or render with F12.

The frog faces -Y (toward the default front view, numpad 1).
Everything is parented to an empty called "Frog", so you can move/scale/rotate it as one.
"""

import math
import bpy

# ------------------------------------------------------------------ settings
CLEAR_SCENE = True        # delete everything in the scene first
ADD_STAGE = True          # ground, lights, camera, background
EXPORT_PATH = ""          # e.g. "C:/tmp/frog.glb" to export a glTF file (blank = skip)

PURPLE = (0.42, 0.13, 0.75, 1.0)
DARK_PURPLE = (0.24, 0.06, 0.45, 1.0)
BELLY = (0.78, 0.62, 0.95, 1.0)
PINK = (1.0, 0.45, 0.65, 1.0)
WHITE = (1.0, 1.0, 1.0, 1.0)
BLACK = (0.01, 0.01, 0.015, 1.0)
MOUTH = (0.12, 0.02, 0.15, 1.0)


# ------------------------------------------------------------------ helpers
def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for block in (bpy.data.meshes, bpy.data.materials, bpy.data.curves, bpy.data.lights):
        for item in list(block):
            if item.users == 0:
                block.remove(item)


def make_material(name, color, roughness=0.45, coat=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = roughness
    for key in ("Coat Weight", "Clearcoat"):  # name differs between versions
        if key in bsdf.inputs:
            bsdf.inputs[key].default_value = coat
            break
    mat.diffuse_color = color
    return mat


def smooth(obj):
    for poly in obj.data.polygons:
        poly.use_smooth = True


def blob(name, loc, scale, mat, parent, rot=(0, 0, 0)):
    """A smooth ellipsoid (UV sphere with radius 1, then scaled)."""
    bpy.ops.mesh.primitive_uv_sphere_add(segments=40, ring_count=20, radius=1, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale
    obj.rotation_euler = tuple(math.radians(a) for a in rot)
    obj.data.materials.append(mat)
    smooth(obj)
    obj.parent = parent
    return obj


def look_at(obj, target):
    con = obj.constraints.new("TRACK_TO")
    con.target = target
    con.track_axis = "TRACK_NEGATIVE_Z"
    con.up_axis = "UP_Y"


# Head ellipsoid: centre (0, -0.75, 1.15), radii (1.05, 0.8, 0.65)
HEAD_C = (0.0, -0.75, 1.15)
HEAD_R = (1.05, 0.8, 0.65)


def head_front_y(x, z):
    """Y coordinate of the head's front surface at a given x and z."""
    t = 1 - (x / HEAD_R[0]) ** 2 - ((z - HEAD_C[2]) / HEAD_R[2]) ** 2
    return HEAD_C[1] - HEAD_R[1] * math.sqrt(max(t, 0.0))


def body_top_z(x, y):
    """Z coordinate of the body's top surface at a given x, y."""
    t = 1 - (x / 1.1) ** 2 - (y / 1.2) ** 2
    return 0.85 + 0.85 * math.sqrt(max(t, 0.0))


# ------------------------------------------------------------------ build
if CLEAR_SCENE:
    clear_scene()

m_skin = make_material("Frog_Purple", PURPLE, roughness=0.35, coat=0.4)
m_dark = make_material("Frog_DarkPurple", DARK_PURPLE, roughness=0.4, coat=0.3)
m_belly = make_material("Frog_Belly", BELLY, roughness=0.45, coat=0.3)
m_pink = make_material("Frog_Blush", PINK, roughness=0.6)
m_white = make_material("Eye_White", WHITE, roughness=0.1, coat=1.0)
m_black = make_material("Eye_Pupil", BLACK, roughness=0.05, coat=1.0)
m_mouth = make_material("Frog_Mouth", MOUTH, roughness=0.5)

root = bpy.data.objects.new("Frog", None)
bpy.context.scene.collection.objects.link(root)

# Body, belly, head
blob("Body", (0, 0, 0.85), (1.1, 1.2, 0.85), m_skin, root)
blob("Belly", (0, -0.45, 0.8), (0.8, 0.9, 0.75), m_belly, root)
blob("Head", HEAD_C, HEAD_R, m_skin, root)

# Eyes (socket bump, eyeball, pupil, highlight)
for side, tag in ((-1, "L"), (1, "R")):
    x = 0.5 * side
    blob(f"EyeSocket_{tag}", (x, -0.85, 1.6), (0.4, 0.4, 0.4), m_skin, root)
    blob(f"Eyeball_{tag}", (x, -0.95, 1.75), (0.3, 0.3, 0.3), m_white, root)
    blob(f"Pupil_{tag}", (x, -1.178, 1.822), (0.15, 0.15, 0.15), m_black, root)
    blob(f"EyeShine_{tag}", (x + 0.06, -1.268, 1.902), (0.045, 0.045, 0.045), m_white, root)

# Smile: a beveled curve hugging the front of the head
curve = bpy.data.curves.new("SmileCurve", "CURVE")
curve.dimensions = "3D"
curve.bevel_depth = 0.03
curve.bevel_resolution = 6
curve.use_fill_caps = True
spline = curve.splines.new("POLY")
smile_pts = [(-0.62, 1.06), (-0.4, 0.98), (-0.2, 0.945), (0.0, 0.935),
             (0.2, 0.945), (0.4, 0.98), (0.62, 1.06)]
spline.points.add(len(smile_pts) - 1)
for pt, (px, pz) in zip(spline.points, smile_pts):
    pt.co = (px, head_front_y(px, pz) - 0.01, pz, 1.0)
smile = bpy.data.objects.new("Smile", curve)
bpy.context.scene.collection.objects.link(smile)
smile.data.materials.append(m_mouth)
smile.parent = root

# Nostrils and blush cheeks
for side, tag in ((-1, "L"), (1, "R")):
    nx, nz = 0.16 * side, 1.3
    blob(f"Nostril_{tag}", (nx, head_front_y(nx, nz) + 0.01, nz), (0.04, 0.03, 0.04), m_mouth, root)
    cx, cz = 0.72 * side, 1.02
    blob(f"Cheek_{tag}", (cx, head_front_y(cx, cz) + 0.02, cz), (0.17, 0.05, 0.1), m_pink, root,
         rot=(0, 0, -20 * side))

# Back legs: thigh, shin, foot with toes
for side, tag in ((-1, "L"), (1, "R")):
    blob(f"Thigh_{tag}", (1.0 * side, 0.4, 0.6), (0.55, 0.85, 0.6), m_skin, root, rot=(0, 0, -15 * side))
    blob(f"Shin_{tag}", (1.15 * side, -0.25, 0.28), (0.22, 0.6, 0.2), m_skin, root, rot=(0, 0, 20 * side))
    blob(f"BackFoot_{tag}", (1.25 * side, -0.85, 0.09), (0.32, 0.5, 0.09), m_dark, root, rot=(0, 0, 15 * side))
    for i, tx in enumerate((-0.2, 0.0, 0.2)):
        blob(f"BackToe_{tag}{i}", (1.25 * side + tx, -1.3, 0.09), (0.11, 0.16, 0.08), m_dark, root)

# Front legs: arm, hand with toes
for side, tag in ((-1, "L"), (1, "R")):
    blob(f"Arm_{tag}", (0.72 * side, -1.0, 0.42), (0.2, 0.2, 0.45), m_skin, root, rot=(-15, 0, 0))
    blob(f"Hand_{tag}", (0.75 * side, -1.22, 0.09), (0.28, 0.32, 0.09), m_dark, root)
    for i, tx in enumerate((-0.14, 0.0, 0.14)):
        blob(f"FrontToe_{tag}{i}", (0.75 * side + tx, -1.5, 0.08), (0.08, 0.13, 0.07), m_dark, root)

# Back spots
spots = [(0.45, 0.5, 0.22), (-0.5, 0.25, 0.18), (0.1, 0.85, 0.16),
         (-0.25, 0.65, 0.12), (0.5, -0.05, 0.13), (-0.55, 0.65, 0.12)]
for i, (sx, sy, sr) in enumerate(spots):
    blob(f"Spot_{i}", (sx, sy, body_top_z(sx, sy) - 0.02), (sr, sr, sr * 0.35), m_dark, root)

# ------------------------------------------------------------------ stage
if ADD_STAGE:
    scene = bpy.context.scene

    # Ground
    bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, 0))
    ground = bpy.context.active_object
    ground.name = "Ground"
    ground.data.materials.append(make_material("Ground", (0.75, 0.85, 0.7, 1.0), roughness=0.9))

    # Target for camera / lights
    target = bpy.data.objects.new("LookTarget", None)
    target.location = (0, -0.4, 1.0)
    scene.collection.objects.link(target)

    # Lights (key, fill, rim)
    def add_light(name, loc, energy, color=(1, 1, 1), size=4.0):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.color = color
        data.size = size
        obj = bpy.data.objects.new(name, data)
        obj.location = loc
        scene.collection.objects.link(obj)
        look_at(obj, target)
        return obj

    add_light("KeyLight", (4, -5, 6), 900, (1.0, 0.95, 0.9))
    add_light("FillLight", (-5, -4, 3), 350, (0.8, 0.85, 1.0), size=5.0)
    add_light("RimLight", (0, 6, 4), 500, (1.0, 0.8, 1.0))

    # Camera
    cam_data = bpy.data.cameras.new("Camera")
    cam_data.lens = 50
    cam = bpy.data.objects.new("Camera", cam_data)
    cam.location = (4.6, -6.2, 3.0)
    scene.collection.objects.link(cam)
    look_at(cam, target)
    scene.camera = cam

    # Background
    try:
        if scene.world is None:
            scene.world = bpy.data.worlds.new("World")
        scene.world.use_nodes = True
        bg = scene.world.node_tree.nodes.get("Background")
        bg.inputs["Color"].default_value = (0.75, 0.82, 0.95, 1.0)
        bg.inputs["Strength"].default_value = 0.8
    except Exception as exc:
        print("World setup skipped:", exc)

    # Render engine (EEVEE's name differs between versions)
    for engine in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = engine
            break
        except TypeError:
            continue

# ------------------------------------------------------------------ export
if EXPORT_PATH:
    bpy.ops.object.select_all(action="DESELECT")
    root.select_set(True)
    for child in root.children:
        child.select_set(True)
    bpy.ops.export_scene.gltf(filepath=EXPORT_PATH, use_selection=True)
    print("Exported to", EXPORT_PATH)

print("Purple frog created!")"""
Simple Purple Frog - Blender script (works in Blender 3.x, 4.x and 5.x)

HOW TO USE
1. Open Blender, go to the "Scripting" workspace.
2. Click "New", paste this whole file, press "Run Script" (Alt+P).
3. Switch the 3D viewport to Material Preview (Z > Material Preview) or render with F12.

The frog faces -Y (toward the default front view, numpad 1).
Everything is parented to an empty called "Frog", so you can move/scale/rotate it as one.
"""

import math
import bpy

# ------------------------------------------------------------------ settings
CLEAR_SCENE = True        # delete everything in the scene first
ADD_STAGE = True          # ground, lights, camera, background
EXPORT_PATH = ""          # e.g. "C:/tmp/frog.glb" to export a glTF file (blank = skip)

PURPLE = (0.42, 0.13, 0.75, 1.0)
DARK_PURPLE = (0.24, 0.06, 0.45, 1.0)
BELLY = (0.78, 0.62, 0.95, 1.0)
PINK = (1.0, 0.45, 0.65, 1.0)
WHITE = (1.0, 1.0, 1.0, 1.0)
BLACK = (0.01, 0.01, 0.015, 1.0)
MOUTH = (0.12, 0.02, 0.15, 1.0)


# ------------------------------------------------------------------ helpers
def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for block in (bpy.data.meshes, bpy.data.materials, bpy.data.curves, bpy.data.lights):
        for item in list(block):
            if item.users == 0:
                block.remove(item)


def make_material(name, color, roughness=0.45, coat=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = roughness
    for key in ("Coat Weight", "Clearcoat"):  # name differs between versions
        if key in bsdf.inputs:
            bsdf.inputs[key].default_value = coat
            break
    mat.diffuse_color = color
    return mat


def smooth(obj):
    for poly in obj.data.polygons:
        poly.use_smooth = True


def blob(name, loc, scale, mat, parent, rot=(0, 0, 0)):
    """A smooth ellipsoid (UV sphere with radius 1, then scaled)."""
    bpy.ops.mesh.primitive_uv_sphere_add(segments=40, ring_count=20, radius=1, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale
    obj.rotation_euler = tuple(math.radians(a) for a in rot)
    obj.data.materials.append(mat)
    smooth(obj)
    obj.parent = parent
    return obj


def look_at(obj, target):
    con = obj.constraints.new("TRACK_TO")
    con.target = target
    con.track_axis = "TRACK_NEGATIVE_Z"
    con.up_axis = "UP_Y"


# Head ellipsoid: centre (0, -0.75, 1.15), radii (1.05, 0.8, 0.65)
HEAD_C = (0.0, -0.75, 1.15)
HEAD_R = (1.05, 0.8, 0.65)


def head_front_y(x, z):
    """Y coordinate of the head's front surface at a given x and z."""
    t = 1 - (x / HEAD_R[0]) ** 2 - ((z - HEAD_C[2]) / HEAD_R[2]) ** 2
    return HEAD_C[1] - HEAD_R[1] * math.sqrt(max(t, 0.0))


def body_top_z(x, y):
    """Z coordinate of the body's top surface at a given x, y."""
    t = 1 - (x / 1.1) ** 2 - (y / 1.2) ** 2
    return 0.85 + 0.85 * math.sqrt(max(t, 0.0))


# ------------------------------------------------------------------ build
if CLEAR_SCENE:
    clear_scene()

m_skin = make_material("Frog_Purple", PURPLE, roughness=0.35, coat=0.4)
m_dark = make_material("Frog_DarkPurple", DARK_PURPLE, roughness=0.4, coat=0.3)
m_belly = make_material("Frog_Belly", BELLY, roughness=0.45, coat=0.3)
m_pink = make_material("Frog_Blush", PINK, roughness=0.6)
m_white = make_material("Eye_White", WHITE, roughness=0.1, coat=1.0)
m_black = make_material("Eye_Pupil", BLACK, roughness=0.05, coat=1.0)
m_mouth = make_material("Frog_Mouth", MOUTH, roughness=0.5)

root = bpy.data.objects.new("Frog", None)
bpy.context.scene.collection.objects.link(root)

# Body, belly, head
blob("Body", (0, 0, 0.85), (1.1, 1.2, 0.85), m_skin, root)
blob("Belly", (0, -0.45, 0.8), (0.8, 0.9, 0.75), m_belly, root)
blob("Head", HEAD_C, HEAD_R, m_skin, root)

# Eyes (socket bump, eyeball, pupil, highlight)
for side, tag in ((-1, "L"), (1, "R")):
    x = 0.5 * side
    blob(f"EyeSocket_{tag}", (x, -0.85, 1.6), (0.4, 0.4, 0.4), m_skin, root)
    blob(f"Eyeball_{tag}", (x, -0.95, 1.75), (0.3, 0.3, 0.3), m_white, root)
    blob(f"Pupil_{tag}", (x, -1.178, 1.822), (0.15, 0.15, 0.15), m_black, root)
    blob(f"EyeShine_{tag}", (x + 0.06, -1.268, 1.902), (0.045, 0.045, 0.045), m_white, root)

# Smile: a beveled curve hugging the front of the head
curve = bpy.data.curves.new("SmileCurve", "CURVE")
curve.dimensions = "3D"
curve.bevel_depth = 0.03
curve.bevel_resolution = 6
curve.use_fill_caps = True
spline = curve.splines.new("POLY")
smile_pts = [(-0.62, 1.06), (-0.4, 0.98), (-0.2, 0.945), (0.0, 0.935),
             (0.2, 0.945), (0.4, 0.98), (0.62, 1.06)]
spline.points.add(len(smile_pts) - 1)
for pt, (px, pz) in zip(spline.points, smile_pts):
    pt.co = (px, head_front_y(px, pz) - 0.01, pz, 1.0)
smile = bpy.data.objects.new("Smile", curve)
bpy.context.scene.collection.objects.link(smile)
smile.data.materials.append(m_mouth)
smile.parent = root

# Nostrils and blush cheeks
for side, tag in ((-1, "L"), (1, "R")):
    nx, nz = 0.16 * side, 1.3
    blob(f"Nostril_{tag}", (nx, head_front_y(nx, nz) + 0.01, nz), (0.04, 0.03, 0.04), m_mouth, root)
    cx, cz = 0.72 * side, 1.02
    blob(f"Cheek_{tag}", (cx, head_front_y(cx, cz) + 0.02, cz), (0.17, 0.05, 0.1), m_pink, root,
         rot=(0, 0, -20 * side))

# Back legs: thigh, shin, foot with toes
for side, tag in ((-1, "L"), (1, "R")):
    blob(f"Thigh_{tag}", (1.0 * side, 0.4, 0.6), (0.55, 0.85, 0.6), m_skin, root, rot=(0, 0, -15 * side))
    blob(f"Shin_{tag}", (1.15 * side, -0.25, 0.28), (0.22, 0.6, 0.2), m_skin, root, rot=(0, 0, 20 * side))
    blob(f"BackFoot_{tag}", (1.25 * side, -0.85, 0.09), (0.32, 0.5, 0.09), m_dark, root, rot=(0, 0, 15 * side))
    for i, tx in enumerate((-0.2, 0.0, 0.2)):
        blob(f"BackToe_{tag}{i}", (1.25 * side + tx, -1.3, 0.09), (0.11, 0.16, 0.08), m_dark, root)

# Front legs: arm, hand with toes
for side, tag in ((-1, "L"), (1, "R")):
    blob(f"Arm_{tag}", (0.72 * side, -1.0, 0.42), (0.2, 0.2, 0.45), m_skin, root, rot=(-15, 0, 0))
    blob(f"Hand_{tag}", (0.75 * side, -1.22, 0.09), (0.28, 0.32, 0.09), m_dark, root)
    for i, tx in enumerate((-0.14, 0.0, 0.14)):
        blob(f"FrontToe_{tag}{i}", (0.75 * side + tx, -1.5, 0.08), (0.08, 0.13, 0.07), m_dark, root)

# Back spots
spots = [(0.45, 0.5, 0.22), (-0.5, 0.25, 0.18), (0.1, 0.85, 0.16),
         (-0.25, 0.65, 0.12), (0.5, -0.05, 0.13), (-0.55, 0.65, 0.12)]
for i, (sx, sy, sr) in enumerate(spots):
    blob(f"Spot_{i}", (sx, sy, body_top_z(sx, sy) - 0.02), (sr, sr, sr * 0.35), m_dark, root)

# ------------------------------------------------------------------ stage
if ADD_STAGE:
    scene = bpy.context.scene

    # Ground
    bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, 0))
    ground = bpy.context.active_object
    ground.name = "Ground"
    ground.data.materials.append(make_material("Ground", (0.75, 0.85, 0.7, 1.0), roughness=0.9))

    # Target for camera / lights
    target = bpy.data.objects.new("LookTarget", None)
    target.location = (0, -0.4, 1.0)
    scene.collection.objects.link(target)

    # Lights (key, fill, rim)
    def add_light(name, loc, energy, color=(1, 1, 1), size=4.0):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.color = color
        data.size = size
        obj = bpy.data.objects.new(name, data)
        obj.location = loc
        scene.collection.objects.link(obj)
        look_at(obj, target)
        return obj

    add_light("KeyLight", (4, -5, 6), 900, (1.0, 0.95, 0.9))
    add_light("FillLight", (-5, -4, 3), 350, (0.8, 0.85, 1.0), size=5.0)
    add_light("RimLight", (0, 6, 4), 500, (1.0, 0.8, 1.0))

    # Camera
    cam_data = bpy.data.cameras.new("Camera")
    cam_data.lens = 50
    cam = bpy.data.objects.new("Camera", cam_data)
    cam.location = (4.6, -6.2, 3.0)
    scene.collection.objects.link(cam)
    look_at(cam, target)
    scene.camera = cam

    # Background
    try:
        if scene.world is None:
            scene.world = bpy.data.worlds.new("World")
        scene.world.use_nodes = True
        bg = scene.world.node_tree.nodes.get("Background")
        bg.inputs["Color"].default_value = (0.75, 0.82, 0.95, 1.0)
        bg.inputs["Strength"].default_value = 0.8
    except Exception as exc:
        print("World setup skipped:", exc)

    # Render engine (EEVEE's name differs between versions)
    for engine in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = engine
            break
        except TypeError:
            continue

# ------------------------------------------------------------------ export
if EXPORT_PATH:
    bpy.ops.object.select_all(action="DESELECT")
    root.select_set(True)
    for child in root.children:
        child.select_set(True)
    bpy.ops.export_scene.gltf(filepath=EXPORT_PATH, use_selection=True)
    print("Exported to", EXPORT_PATH)

print("Purple frog created!")
