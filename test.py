import json
import pytest
from decimal import Decimal as D
from main import (
    SolarSupportersPlacer,
    DataValidator,
    PANEL_WIDTH,
    EDGE_CLEARANCE,
    SPAN_LIMIT,
)


def p(x, y):
    return {"x": D(str(x)), "y": D(str(y))}


GAP = D("0.35")


def max_mount_spacing(mounts: list[dict]) -> float:
    xs_by_y: dict[float, list[float]] = {}
    for m in mounts:
        xs_by_y.setdefault(m["y"], []).append(m["x"])
    worst = 0.0
    for xs in xs_by_y.values():
        xs.sort()
        for a, b in zip(xs, xs[1:]):
            worst = max(worst, b - a)
    return worst


# DataValidator


def test_validator_rejects_non_list():
    with pytest.raises(TypeError):
        DataValidator().validate("not a list")


def test_validator_rejects_missing_key():
    with pytest.raises(TypeError):
        DataValidator().validate([{"x": 0}])


def test_validator_rejects_extra_key():
    with pytest.raises(TypeError):
        DataValidator().validate([{"x": 0, "y": 0, "z": 0}])


def test_validator_rejects_non_numeric_value():
    with pytest.raises(TypeError):
        DataValidator().validate([{"x": "abc", "y": 0}])


def test_validator_rejects_overlapping_panels():
    with pytest.raises(ValueError, match="overlap"):
        DataValidator().validate([{"x": 0, "y": 0}, {"x": 10, "y": 0}])


def test_validator_accepts_valid_panels():
    result = DataValidator().validate([{"x": 0, "y": 0}, {"x": 45.05, "y": 0}])
    assert len(result) == 2
    assert isinstance(result[0]["x"], D)


# SolarSupportersPlacer


def test_empty_panels_returns_empty_result():
    result = SolarSupportersPlacer().place([])
    assert result == {"mounts": [], "joints": []}


def test_two_panels_gap_exactly_joint_gap_produces_no_joints():
    from main import JOINT_GAP
    panels = [p(0, 0), p(PANEL_WIDTH + JOINT_GAP, 0)]
    result = SolarSupportersPlacer().place(panels)
    assert result["joints"] == []


def test_single_panel():
    panels = [p(0, 0)]
    result = SolarSupportersPlacer().place(panels)

    assert len(result["mounts"]) == 4
    assert len(result["joints"]) == 0

    for m in result["mounts"]:
        assert float(EDGE_CLEARANCE) <= m["x"] <= float(PANEL_WIDTH - EDGE_CLEARANCE)


def test_single_panel_offset():
    offset = 100
    panels = [p(offset, 0)]
    result = SolarSupportersPlacer().place(panels)

    assert len(result["mounts"]) == 4
    for m in result["mounts"]:
        assert (
            offset + float(EDGE_CLEARANCE)
            <= m["x"]
            <= offset + float(PANEL_WIDTH - EDGE_CLEARANCE)
        )


def test_five_panels_in_a_row():
    panels = [p(i * (PANEL_WIDTH + GAP), 0) for i in range(5)]
    result = SolarSupportersPlacer().place(panels)

    assert len(result["mounts"]) == 12
    assert len(result["joints"]) == 8

    assert max_mount_spacing(result["mounts"]) <= float(SPAN_LIMIT)

    x_min = 0.0
    x_max = float(4 * (PANEL_WIDTH + GAP) + PANEL_WIDTH)
    for m in result["mounts"]:
        assert x_min <= m["x"] <= x_max


def test_three_panels_with_large_gaps():
    big_gap = D("20")
    panels = [p(i * (PANEL_WIDTH + big_gap), 0) for i in range(3)]
    result = SolarSupportersPlacer().place(panels)

    assert len(result["mounts"]) == 12
    assert len(result["joints"]) == 0

    assert max_mount_spacing(result["mounts"]) <= float(SPAN_LIMIT)


def test_overlapping_panels_raises():
    panels = [p(0, 0), p(10, 0)]
    with pytest.raises(ValueError, match="overlap"):
        SolarSupportersPlacer().place(panels)


def test_incompatible_segments_raises():
    row0 = [p(i * (PANEL_WIDTH + GAP), 0) for i in range(4)]
    row1 = [p(i * (PANEL_WIDTH + GAP), 71.6) for i in range(9)]
    with pytest.raises(ValueError, match="No common first rafter position"):
        SolarSupportersPlacer().place(row0 + row1)


def test_task_example():
    with open("input.json") as f:
        data = json.load(f)
    panels = [{"x": D(str(p["x"])), "y": D(str(p["y"]))} for p in data]

    result = SolarSupportersPlacer().place(panels)

    assert len(result["mounts"]) == 28
    assert len(result["joints"]) == 12
