import json
import tkinter as tk
from decimal import Decimal
from main import PanelPos, PANEL_WIDTH, PANEL_HEIGHT

MARGIN = 40
SCALE = 3.5
JOINT_SIZE = 2.5
MOUNT_RADIUS = 1.5


def to_canvas(x: float, y: float, canvas_height: float) -> tuple[float, float]:
    return MARGIN + x * SCALE, canvas_height - MARGIN - y * SCALE


def visualise(panels: list[PanelPos], joints: list[dict], mounts: list[dict]) -> None:
    all_x = [float(p["x"]) for p in panels] + [
        float(p["x"]) + float(PANEL_WIDTH) for p in panels
    ]
    all_y = [float(p["y"]) for p in panels] + [
        float(p["y"]) + float(PANEL_HEIGHT) for p in panels
    ]
    width = (max(all_x) - min(all_x)) * SCALE + 2 * MARGIN
    height = (max(all_y) - min(all_y)) * SCALE + 2 * MARGIN

    root = tk.Tk()
    root.title("Solar array layout")
    canvas = tk.Canvas(root, width=int(width), height=int(height), bg="white")
    canvas.pack()

    for panel in panels:
        x0, y0 = to_canvas(
            float(panel["x"]), float(panel["y"]) + float(PANEL_HEIGHT), height
        )
        x1, y1 = to_canvas(
            float(panel["x"]) + float(PANEL_WIDTH), float(panel["y"]), height
        )
        canvas.create_rectangle(
            x0, y0, x1, y1, fill="#4682b4", outline="black", width=1
        )

    for joint in joints:
        cx, cy = to_canvas(joint["x"], joint["y"], height)
        half = JOINT_SIZE * SCALE / 2
        canvas.create_rectangle(
            cx - half, cy - half, cx + half, cy + half, fill="gray", outline=""
        )

    for mount in mounts:
        cx, cy = to_canvas(mount["x"], mount["y"], height)
        r = MOUNT_RADIUS * SCALE
        canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill="black", outline="")

    root.mainloop()


if __name__ == "__main__":
    with open("input.json") as f:
        data = json.load(f)
    panels: list[PanelPos] = [
        {"x": Decimal(str(p["x"])), "y": Decimal(str(p["y"]))} for p in data
    ]

    with open("output.json") as f:
        output = json.load(f)

    visualise(panels, output["joints"], output["mounts"])
