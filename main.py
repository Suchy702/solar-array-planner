import json
from decimal import Decimal
from typing import TypedDict


class PanelPos(TypedDict):
    x: Decimal
    y: Decimal


class CornerPos(TypedDict):
    x: Decimal
    y: Decimal


PANEL_WIDTH = Decimal("44.7")
PANEL_HEIGHT = Decimal("71.1")
RAFTER_SPACING = Decimal("16")
EDGE_CLEARANCE = Decimal("2")
CANTILEVER_LIMIT = Decimal("16")
SPAN_LIMIT = Decimal("48")
JOINT_GAP = Decimal("1")


class DataValidator:
    def validate(self, panels: object) -> list[PanelPos]:
        if not isinstance(panels, list):
            raise TypeError("panels must be a list")
        result: list[PanelPos] = []
        for i, item in enumerate(panels):
            if not isinstance(item, dict) or set(item.keys()) != {"x", "y"}:
                raise TypeError(f"panels[{i}] must be a dict with exactly keys 'x' and 'y'")
            for key in ("x", "y"):
                if not isinstance(item[key], (int, float, Decimal)):
                    raise TypeError(f"panels[{i}]['{key}'] must be a number")
            result.append({"x": Decimal(str(item["x"])), "y": Decimal(str(item["y"]))})

        by_x = sorted(enumerate(result), key=lambda t: t[1]["x"])
        for k in range(len(by_x) - 1):
            i, a = by_x[k]
            j, b = by_x[k + 1]
            if b["x"] < a["x"] + PANEL_WIDTH:
                if a["y"] < b["y"] + PANEL_HEIGHT and b["y"] < a["y"] + PANEL_HEIGHT:
                    raise ValueError(f"panels[{i}] and panels[{j}] overlap")

        by_y = sorted(enumerate(result), key=lambda t: t[1]["y"])
        for k in range(len(by_y) - 1):
            i, a = by_y[k]
            j, b = by_y[k + 1]
            if b["y"] < a["y"] + PANEL_HEIGHT:
                if a["x"] < b["x"] + PANEL_WIDTH and b["x"] < a["x"] + PANEL_WIDTH:
                    raise ValueError(f"panels[{i}] and panels[{j}] overlap")

        return result


class JointsPlacer:
    connections: dict[tuple[Decimal, Decimal], list[tuple[Decimal, Decimal]]] = {}

    def divide_to_corners(self, panels: list[PanelPos]) -> list[CornerPos]:
        """Expands each panel's top-left corner into all four corner positions."""
        corners: list[CornerPos] = []
        for panel in panels:
            x, y = panel["x"], panel["y"]
            corners.append({"x": x,                  "y": y})
            corners.append({"x": x + PANEL_WIDTH,     "y": y})
            corners.append({"x": x,                  "y": y + PANEL_HEIGHT})
            corners.append({"x": x + PANEL_WIDTH,     "y": y + PANEL_HEIGHT})
        return corners

    def divide_to_rows(self, panels: list[CornerPos]) -> list[list[CornerPos]]:
        """Groups corners by y coordinate, each row sorted by x ascending."""
        rows: dict[Decimal, list[CornerPos]] = {}
        for corner in panels:
            rows.setdefault(corner["y"], []).append(corner)
        return [sorted(row, key=lambda p: p["x"]) for row in rows.values()]

    def divide_to_columns(self, panels: list[CornerPos]) -> list[list[CornerPos]]:
        """Groups corners by x coordinate, each column sorted by y ascending."""
        columns: dict[Decimal, list[CornerPos]] = {}
        for corner in panels:
            columns.setdefault(corner["x"], []).append(corner)
        return [sorted(col, key=lambda p: p["y"]) for col in columns.values()]

    def find_connections(self, panels: list[PanelPos]) -> None:
        """Populates connections: maps each corner to its neighbours whose edge distance is less than 1."""
        corners = self.divide_to_corners(panels)
        self.connections = {}

        def _key(c: CornerPos) -> tuple[Decimal, Decimal]:
            return (c["x"], c["y"])

        def _register(a: CornerPos, b: CornerPos) -> None:
            self.connections.setdefault(_key(a), []).append(_key(b))
            self.connections.setdefault(_key(b), []).append(_key(a))

        for row in self.divide_to_rows(corners):
            for i in range(len(row) - 1):
                a, b = row[i], row[i + 1]
                if b["x"] - a["x"] < JOINT_GAP:
                    _register(a, b)

        for col in self.divide_to_columns(corners):
            for i in range(len(col) - 1):
                a, b = col[i], col[i + 1]
                if b["y"] - a["y"] < JOINT_GAP:
                    _register(a, b)

    def _is_vertical_pair(self, group: list[tuple[Decimal, Decimal]]) -> bool:
        return len(group) == 2 and group[0][0] == group[1][0]

    def find_joints_positions(self, panels: list[PanelPos]) -> list[tuple[Decimal, Decimal]]:
        """Returns joint center positions, merging groups of up to 4 connected corners into a single point."""
        self.find_connections(panels)
        sorted_connections = sorted(self.connections.items(), key=lambda item: len(item[1]), reverse=True)
        already_jointed: set[tuple[Decimal, Decimal]] = set()
        joints: list[tuple[Decimal, Decimal]] = []

        for corner, neighbours in sorted_connections:
            if corner in already_jointed:
                continue

            group = [corner, *neighbours]
            already_jointed.update(group)

            if self._is_vertical_pair(group):
                continue

            xs = [p[0] for p in group]
            ys = [p[1] for p in group]
            center = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)
            joints.append(center)

        return joints


class MountsPlacer:
    segments: list[list[PanelPos]] = []
    bias: Decimal = Decimal("0")

    def _compute_and_apply_bias(self, panels: list[PanelPos]) -> list[PanelPos]:
        self.bias = min(p["x"] for p in panels)
        return [{"x": p["x"] - self.bias, "y": p["y"]} for p in panels]

    def choose_first_rafter_position(self, panels: list[PanelPos]) -> Decimal:
        normalized = self._compute_and_apply_bias(panels)
        self.divide_to_segments(normalized)

        feasible_min = Decimal("-Infinity")
        feasible_max = Decimal("Infinity")

        for segment in self.segments:
            x_start = min(p["x"] for p in segment)
            x_end = max(p["x"] for p in segment) + PANEL_WIDTH

            n = int((x_end - x_start - 2 * EDGE_CLEARANCE) / RAFTER_SPACING)

            width = x_end - x_start

            l_min = EDGE_CLEARANCE
            l_max = RAFTER_SPACING
            p_min = width - RAFTER_SPACING - n * RAFTER_SPACING
            p_max = width - EDGE_CLEARANCE - n * RAFTER_SPACING

            seg_min = max(l_min, p_min)
            seg_max = min(l_max, p_max)

            if seg_min > seg_max:
                raise ValueError(f"No valid rafter position for segment x={x_start}..{x_end}")

            feasible_min = max(feasible_min, seg_min)
            feasible_max = min(feasible_max, seg_max)

        if feasible_min > feasible_max:
            raise ValueError("No common first rafter position exists across all segments")

        return feasible_min

    def find_mounts_positions(self, panels: list[PanelPos]) -> list[tuple[Decimal, Decimal]]:
        r0 = self.choose_first_rafter_position(panels)
        mounts = []
        step = int(SPAN_LIMIT / RAFTER_SPACING)

        def add_mount(x: Decimal, panel: PanelPos) -> None:
            mounts.append((x, panel["y"]))
            mounts.append((x, panel["y"] + PANEL_HEIGHT))

        for segment in self.segments:
            segment_sorted = sorted(segment, key=lambda p: p["x"])
            x_start = segment_sorted[0]["x"]
            x_end = segment_sorted[-1]["x"] + PANEL_WIDTH

            current_rafter = x_start + r0

            add_mount(current_rafter, segment_sorted[0])
            add_mount(x_end - r0, segment_sorted[-1])

            i = 1
            while i < len(segment_sorted):
                panel = segment_sorted[i]
                current_rafter += step * RAFTER_SPACING

                if current_rafter < panel["x"] + EDGE_CLEARANCE:
                    current_rafter -= RAFTER_SPACING
                    add_mount(current_rafter, panel)
                    continue

                if current_rafter > panel["x"] + PANEL_WIDTH - EDGE_CLEARANCE:
                    current_rafter -= RAFTER_SPACING
                    add_mount(current_rafter, panel)
                    i += 1
                    continue

                add_mount(current_rafter, panel)
                i += 1

        return [(x + self.bias, y) for x, y in mounts]

    def divide_to_segments(self, panels: list[PanelPos]) -> None:
        """Groups panels into horizontal segments; breaks the segment when the gap between adjacent panels exceeds 1."""
        rows = {}
        for panel in panels:
            rows.setdefault(panel["y"], []).append(panel)

        self.segments = []
        for row in rows.values():
            row_sorted = sorted(row, key=lambda p: p["x"])
            current = [row_sorted[0]]
            for prev, next_ in zip(row_sorted, row_sorted[1:]):
                if next_["x"] - (prev["x"] + PANEL_WIDTH) > JOINT_GAP:
                    self.segments.append(current)
                    current = []
                current.append(next_)
            self.segments.append(current)


class SolarSupportersPlacer:
    def place(self, panels: object) -> dict:
        validated = DataValidator().validate(panels)
        mounts_placer = MountsPlacer()
        joints_placer = JointsPlacer()

        raw_mounts = mounts_placer.find_mounts_positions(validated)
        raw_joints = joints_placer.find_joints_positions(validated)

        return {
            "mounts": [{"x": float(x), "y": float(y)} for x, y in raw_mounts],
            "joints": [{"x": float(x), "y": float(y)} for x, y in raw_joints],
        }


if __name__ == "__main__":
    with open("input.json") as f:
        data = json.load(f)
    result = SolarSupportersPlacer().place(data)

    with open("output.json", "w") as f:
        json.dump(result, f, indent=2)
