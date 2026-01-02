import os
import Sofa


class RodCutController(Sofa.Core.Controller):
    def __init__(
        self,
        rod_mo,
        dofs,
        topo,
        topo_mod,
        topo_proc,
        center,
        half,
        speed=8.0,
        dt=0.02,
        rigid=False,
    ):
        super().__init__()
        self.listening = True
        self.rod_mo = rod_mo
        self.dofs = dofs
        self.topo = topo
        self.topo_mod = topo_mod
        self.topo_proc = topo_proc
        self.center = list(center)
        self.half = list(half)
        self.speed = speed
        self.dt = dt
        self.rigid = rigid
        self.keys_down = set()
        self.cut_enabled = False
        self._arrow_codes = {"\x13": "up", "\x15": "down", "\x12": "left", "\x14": "right"}
        self._qt_key_map = {
            16777234: "left",
            16777235: "up",
            16777236: "right",
            16777237: "down",
            16777238: "pageup",
            16777239: "pagedown",
        }
        self._qt_ignore = {
            16777248,  # shift
            16777249,  # control
            16777250,  # meta
            16777251,  # alt
            16777252,  # altgr
        }
        self._ignore_keys = {"shift", "control", "ctrl", "alt", "altgr", "meta", "super", "capslock", "numlock"}
        self._move_map = {
            "8": (0.0, 0.0, 1.0),
            "2": (0.0, 0.0, -1.0),
            "4": (-1.0, 0.0, 0.0),
            "6": (1.0, 0.0, 0.0),
            "9": (0.0, 1.0, 0.0),
            "3": (0.0, -1.0, 0.0),
            "up": (0.0, 0.0, 1.0),
            "down": (0.0, 0.0, -1.0),
            "left": (-1.0, 0.0, 0.0),
            "right": (1.0, 0.0, 0.0),
            "pageup": (0.0, 1.0, 0.0),
            "pagedown": (0.0, -1.0, 0.0),
        }
        self._update_rod_positions()
        print("[INFO] Rod control: keypad 8/2=Z+,Z- 4/6=X-,X+ 9/3=Y+,Y-")
        print("[INFO] P=toggle cut, R=reset rod")

    def onKeypressedEvent(self, event):
        self._dispatch_key_event(event, pressed=True)

    def onKeyreleasedEvent(self, event):
        self._dispatch_key_event(event, pressed=False)

    def onKeyPressedEvent(self, event):
        self._dispatch_key_event(event, pressed=True)

    def onKeyReleasedEvent(self, event):
        self._dispatch_key_event(event, pressed=False)

    def handleEvent(self, event):
        self._dispatch_key_event(event, pressed=None)

    def onAnimateBeginEvent(self, _event):
        dx, dy, dz = self._movement_direction()
        if dx or dy or dz:
            self._apply_delta(dx * self.speed * self.dt, dy * self.speed * self.dt, dz * self.speed * self.dt)
        if self.cut_enabled:
            self._cut_at_rod()

    def _event_key(self, event):
        if isinstance(event, dict):
            return event.get("key")
        if hasattr(event, "__getitem__"):
            try:
                return event["key"]
            except Exception:
                pass
        if hasattr(event, "getKey"):
            return event.getKey()
        return None

    def _normalize_key(self, key):
        if key is None:
            return None
        if hasattr(key, "value"):
            key = key.value
        if isinstance(key, int):
            if key in self._qt_key_map:
                return self._qt_key_map[key]
            if key in self._qt_ignore:
                return None
            if 32 <= key < 127:
                return chr(key).lower()
            return str(key).lower()
        if isinstance(key, str):
            if key in self._arrow_codes:
                return self._arrow_codes[key]
            k = key.strip().lower()
            if k.startswith("qt.key_"):
                k = k[7:]
            if k.startswith("key_"):
                k = k[4:]
            if k.startswith("kp_"):
                k = k[3:]
            elif k.startswith("kp"):
                k = k[2:]
            if k in ("pgup",):
                k = "pageup"
            if k in ("pgdn",):
                k = "pagedown"
            if k.isdigit():
                code = int(k)
                if code in self._qt_key_map:
                    return self._qt_key_map[code]
                if 32 <= code < 127:
                    return chr(code).lower()
                return k
            if k in self._ignore_keys:
                return None
            return k
        try:
            k = chr(int(key))
            if k in self._arrow_codes:
                return self._arrow_codes[k]
            return k.lower()
        except (TypeError, ValueError, OverflowError):
            return str(key).lower()

    def _is_move_key(self, key):
        return key in self._move_map

    def _nudge_once(self, key):
        step = self.speed * self.dt
        dx, dy, dz = 0.0, 0.0, 0.0
        if key in self._move_map:
            mx, my, mz = self._move_map[key]
            dx = mx * step
            dy = my * step
            dz = mz * step
        self._apply_delta(dx, dy, dz)

    def _apply_delta(self, dx, dy, dz):
        if dx == 0.0 and dy == 0.0 and dz == 0.0:
            return
        self.center[0] += dx
        self.center[1] += dy
        self.center[2] += dz
        self._update_rod_positions()

    def _movement_direction(self):
        dx = dy = dz = 0.0
        for key in self.keys_down:
            if key in self._move_map:
                mx, my, mz = self._move_map[key]
                dx += mx
                dy += my
                dz += mz
        return dx, dy, dz

    def _dispatch_key_event(self, event, pressed=None):
        key = self._normalize_key(self._event_key(event))
        if not key:
            return
        if pressed is None:
            if hasattr(event, "getClassName"):
                name = event.getClassName().lower()
                if "keyreleased" in name:
                    pressed = False
                elif "keypressed" in name:
                    pressed = True
        if pressed is None:
            return
        if pressed is False:
            handled = self._handle_key_release(key)
        else:
            handled = self._handle_key_press(key)
        if handled and hasattr(event, "setHandled"):
            event.setHandled()

    def _handle_key_press(self, key):
        if key in self.keys_down:
            return True
        if key == "p":
            self.cut_enabled = not self.cut_enabled
            state = "ON" if self.cut_enabled else "OFF"
            print(f"[INFO] Cut mode: {state}")
            self.keys_down.add(key)
            return True
        if key == "r":
            self.center = [0.0, 0.0, 0.0]
            self._update_rod_positions()
            self.keys_down.add(key)
            return True
        if self._is_move_key(key):
            self.keys_down.add(key)
            self._nudge_once(key)
            return True
        return False

    def _handle_key_release(self, key):
        if key == "p":
            return True
        if key in self.keys_down:
            self.keys_down.remove(key)
            return True
        return False

    def _update_rod_positions(self):
        data = getattr(self.rod_mo, "position", None)
        if data is None:
            return
        if self.rigid:
            cx, cy, cz = self.center
            pose = [cx, cy, cz, 0.0, 0.0, 0.0, 1.0]
            if hasattr(data, "value"):
                data.value = [pose]
            else:
                self.rod_mo.position = [pose]
            return
        hx, hy, hz = self.half
        cx, cy, cz = self.center
        positions = [
            [cx - hx, cy - hy, cz - hz],
            [cx + hx, cy - hy, cz - hz],
            [cx + hx, cy + hy, cz - hz],
            [cx - hx, cy + hy, cz - hz],
            [cx - hx, cy - hy, cz + hz],
            [cx + hx, cy - hy, cz + hz],
            [cx + hx, cy + hy, cz + hz],
            [cx - hx, cy + hy, cz + hz],
        ]
        if hasattr(data, "value"):
            data.value = positions
        else:
            self.rod_mo.position = positions

    def _get_positions(self, mo):
        pos = getattr(mo, "position", None)
        if pos is None:
            return []
        return getattr(pos, "value", pos)

    def _get_tetras(self, topo):
        tetras = getattr(topo, "tetrahedra", None)
        if tetras is None:
            return []
        return getattr(tetras, "value", tetras)

    def _cut_at_rod(self):
        positions = self._get_positions(self.dofs)
        tetras = self._get_tetras(self.topo)
        if positions is None or tetras is None:
            return
        if len(positions) == 0 or len(tetras) == 0:
            return
        hx, hy, hz = self.half
        cx, cy, cz = self.center
        rod_min_x = cx - hx
        rod_max_x = cx + hx
        rod_min_y = cy - hy
        rod_max_y = cy + hy
        rod_min_z = cz - hz
        rod_max_z = cz + hz
        to_remove = []
        for i, tet in enumerate(tetras):
            p0 = positions[tet[0]]
            p1 = positions[tet[1]]
            p2 = positions[tet[2]]
            p3 = positions[tet[3]]
            min_x = min(p0[0], p1[0], p2[0], p3[0])
            max_x = max(p0[0], p1[0], p2[0], p3[0])
            if max_x < rod_min_x or min_x > rod_max_x:
                continue
            min_y = min(p0[1], p1[1], p2[1], p3[1])
            max_y = max(p0[1], p1[1], p2[1], p3[1])
            if max_y < rod_min_y or min_y > rod_max_y:
                continue
            min_z = min(p0[2], p1[2], p2[2], p3[2])
            max_z = max(p0[2], p1[2], p2[2], p3[2])
            if max_z < rod_min_z or min_z > rod_max_z:
                continue
            if (
                max_x >= rod_min_x
                and min_x <= rod_max_x
                and max_y >= rod_min_y
                and min_y <= rod_max_y
                and max_z >= rod_min_z
                and min_z <= rod_max_z
            ):
                to_remove.append(i)
        if to_remove:
            removed = sorted(to_remove, reverse=True)
            if self.topo_proc is not None:
                self.topo_proc.tetrahedraToRemove = removed
                print(f"[INFO] Cut removed {len(removed)} tetras at rod {self.center}")
            else:
                print("[WARNING] Cut skipped: TopologicalChangeProcessor missing")
        else:
            if self.topo_proc is not None:
                self.topo_proc.tetrahedraToRemove = []


def createScene(root):
    root.addObject("RequiredPlugin", name="SofaPython3")
    plugins = [
        "Sofa.Component.AnimationLoop",
        "Sofa.Component.Collision.Detection.Algorithm",
        "Sofa.Component.Collision.Detection.Intersection",
        "Sofa.Component.Collision.Geometry",
        "Sofa.Component.Collision.Response.Contact",
        "Sofa.Component.Constraint.Projective",
        "Sofa.Component.IO.Mesh",
        "Sofa.Component.LinearSolver.Iterative",
        "Sofa.Component.Mapping.Linear",
        "Sofa.Component.Mapping.NonLinear",
        "Sofa.Component.Mass",
        "Sofa.Component.ODESolver.Backward",
        "Sofa.Component.Engine.Transform",
        "Sofa.Component.Setting",
        "Sofa.Component.Engine.Select",
        "Sofa.Component.SolidMechanics.FEM.Elastic",
        "Sofa.Component.SolidMechanics.Spring",
        "Sofa.Component.StateContainer",
        "Sofa.Component.Topology.Container.Dynamic",
        "Sofa.Component.Topology.Mapping",
        "Sofa.Component.Topology.Utility",
        "Sofa.Component.Visual",
        "Sofa.GUI.Component",
        "Sofa.GL.Component.Rendering3D",
    ]
    for p in plugins:
        root.addObject("RequiredPlugin", name=p)

    root.addObject(
        "VisualStyle",
        displayFlags="showVisualModels showBehaviorModels showCollisionModels",
    )
    root.gravity = [0, -9.81, 0]
    root.dt = 0.02
    root.addObject("DefaultAnimationLoop")

    # Collision pipeline (for picking)
    root.addObject("CollisionPipeline", name="CollisionPipeline", verbose=0)
    root.addObject("BruteForceBroadPhase")
    root.addObject("BVHNarrowPhase")
    root.addObject("DefaultContactManager", name="collision response", response="PenalityContactForceField")
    root.addObject("DiscreteIntersection")

    # Viewer + mouse settings
    settings = root.addChild("Settings")
    settings.addObject("SofaDefaultPathSetting")
    app = settings.addChild("Application")
    app.addObject(
        "VisualStyle",
        displayFlags="showVisual hideBehaviorModels hideForceFields hideCollision hideMapping hideOptions",
    )
    app.addObject("ViewerSetting", fullscreen=0, objectPickingMethod="Ray casting")
    app.addObject("BackgroundSetting", color="0.2 0 0.2")
    app.addObject("StatsSetting", logTime=0)
    mouse = settings.addChild("MouseConfiguration")
    mouse.addObject(
        "VisualStyle",
        displayFlags="showVisual hideBehaviorModels hideForceFields hideCollision hideMapping hideOptions",
    )
    # Shift + Left: pull; Shift + Right: fix
    mouse.addObject("AttachBodyButtonSetting", button="Left", stiffness=5000, arrowSize=0.2)
    mouse.addObject("FixPickedParticleButtonSetting", button="Right", stiffness=10000)

    # Rod tool (keyboard-controlled cutter)
    rod = root.addChild("RodTool")
    rod_center = [-5.0, 2.0, 0.0]
    rod_half = [0.12, 0.12, 2.5]
    hx, hy, hz = rod_half
    cx, cy, cz = rod_center
    rod_positions = [
        [cx - hx, cy - hy, cz - hz],
        [cx + hx, cy - hy, cz - hz],
        [cx + hx, cy + hy, cz - hz],
        [cx - hx, cy + hy, cz - hz],
        [cx - hx, cy - hy, cz + hz],
        [cx + hx, cy - hy, cz + hz],
        [cx + hx, cy + hy, cz + hz],
        [cx - hx, cy + hy, cz + hz],
    ]
    rod_triangles = [
        [0, 1, 2],
        [0, 2, 3],
        [4, 5, 6],
        [4, 6, 7],
        [0, 1, 5],
        [0, 5, 4],
        [1, 2, 6],
        [1, 6, 5],
        [2, 3, 7],
        [2, 7, 6],
        [3, 0, 4],
        [3, 4, 7],
    ]
    rod.addObject("TriangleSetTopologyContainer", name="topo", triangles=rod_triangles)
    rod.addObject("TriangleSetGeometryAlgorithms")
    rod_mo = rod.addObject("MechanicalObject", name="dofs", position=rod_positions)
    rod_visu = rod.addChild("Visu")
    rod_visu.addObject(
        "OglModel",
        name="Visual",
        position=rod_positions,
        triangles=rod_triangles,
        color=[1.0, 1.0, 1.0, 1.0],
        tags="NoPicking",
    )
    rod_visu.addObject("IdentityMapping", input="@../dofs", output="@Visual")
    rod_is_rigid = False

    # Liver volume
    scene_dir = os.path.dirname(os.path.abspath(__file__))
    msh_path = os.path.join(scene_dir, "liver3-HD.msh")
    liver = root.addChild("Liver")
    liver.addObject("EulerImplicitSolver", rayleighStiffness=0.1, rayleighMass=0.1)
    liver.addObject("CGLinearSolver", iterations=25, tolerance=1e-9, threshold=1e-9)
    loader = liver.addObject("MeshGmshLoader", name="meshLoader", filename=msh_path)
    dofs = liver.addObject("MechanicalObject", name="dofs", src="@meshLoader")
    topo = liver.addObject("TetrahedronSetTopologyContainer", name="topo", src="@meshLoader", listening=True)
    topo_mod = liver.addObject("TetrahedronSetTopologyModifier", listening=True)
    topo_proc = liver.addObject(
        "TopologicalChangeProcessor",
        listening=True,
        useDataInputs=True,
        timeToRemove=0.0,
        interval=root.dt.value,
    )
    liver.addObject("TetrahedronSetGeometryAlgorithms")
    liver.addObject("DiagonalMass", massDensity=1.0)
    liver.addObject(
        "TetrahedralCorotationalFEMForceField",
        name="FEM",
        method="large",
        poissonRatio=0.3,
        youngModulus=500.0,
        computeGlobalMatrix=False,
    )

    liver.addObject(
        "BoxROI",
        name="fixedBox",
        box=[-11.0, -3.0, 5.5, 7.0, 7.0, 6.9],
        drawBoxes=False,
    )
    liver.addObject("FixedConstraint", indices="@fixedBox.indices")

    # Surface generated from volume (guaranteed to follow deformation)
    surface = liver.addChild("Surface")
    surface.addObject("TriangleSetTopologyContainer", name="surfTopo", listening=True)
    surface.addObject("TriangleSetTopologyModifier", listening=True)
    surface.addObject("TriangleSetGeometryAlgorithms")
    surface.addObject(
        "Tetra2TriangleTopologicalMapping",
        input="@../topo",
        output="@surfTopo",
        listening=True,
    )
    surface.addObject("MechanicalObject", name="surfDofs", position="@../dofs.position")
    surface.addObject("IdentityMapping", input="@../dofs", output="@surfDofs")
    surface.addObject("TriangleCollisionModel", moving=True, simulated=True)
    surface.addObject("LineCollisionModel", moving=True, simulated=True)
    surface.addObject("PointCollisionModel", moving=True, simulated=True)

    visu = surface.addChild("Visu")
    visu.addObject("OglModel", name="Visual", color=[0.9, 0.5, 0.3, 1.0])
    visu.addObject("IdentityMapping", input="@../surfDofs", output="@Visual")

    root.addObject(
        RodCutController(
            rod_mo,
            dofs,
            topo,
            topo_mod,
            topo_proc,
            rod_center,
            rod_half,
            speed=8.0,
            dt=root.dt.value,
            rigid=rod_is_rigid,
        )
    )

    return root
