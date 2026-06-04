# Solar Array Planner

## Usage

**Requirements:** Python 3.9+, no external dependencies.

1. Define the panel layout in `input.json` as a list of `{"x": <number>, "y": <number>}` objects (top-left corner of each panel).
2. Run the planner:
   ```bash
   python3 main.py
   ```
3. Results are written to `output.json` with two keys:
   - `mounts` — list of mount positions `{"x": ..., "y": ...}`
   - `joints` — list of joint positions `{"x": ..., "y": ...}`

To run the visualiser (requires `tkinter`):
```bash
python3 visualiser.py
```

<img width="70%" height="70%" alt="image" src="https://github.com/user-attachments/assets/013ce81a-9f15-4c8f-96ca-3c06e1c72c79" />

Visualisation of mounts and joints of test data.

To run the tests (requires `pytest`):
```bash
python3 -m pytest test.py -v
```

---

## Observations & Assumptions

### Complexity
The solution has a time complexity of `O(nlogn)`, where `n` is the number of panels.

### Span Limit

> The distance between any two consecutive supports on a single panel cannot exceed 48 units.

This condition is always satisfied as-is, since a single panel is only 44.7 units wide. Based on the reference diagram, the intended interpretation is the distance between **segments** of panels, not individual ones.

I assumed a mount can support a single panel at a time (as opposed to two simultaneously, which the diagram might suggest).

The diagram contains an error, it marks where an additional mount should be placed because a single panel is not part of the group above it, violating the Cantilever Limit condition.

<img width="70%" height="70%" alt="image" src="https://github.com/user-attachments/assets/00286175-700b-44fc-b1d8-98b39b3757b6" />

I also assume there is no limit on the number of panels in a group, and that "continuous segment of panels" applies to a single panel as well, as suggested by the bottom-right mount on the bottom-left panel in the diagram.

---

## When Panel Placement Is Impossible

Placement fails in two cases:

1. **Panels overlap each other.**
2. **No valid rafter spacing exists** that satisfies both the Span Limit and Cantilever Limit conditions.

### Valid Rafter Range Derivation

To determine the valid range for placing the first rafter, let:

| Variable | Description |
|----------|-------------|
| `R_0` | Position of the first rafter |
| `x_start` | Left edge of the panel segment |
| `x_end` | Right edge of the panel segment |

From the problem constraints:

```
x_start + 2  <=  R_0  <=  x_start + 16
```

For the last rafter `R_last` (which must support the last panel):

```
x_end - 2  <=  R_last  <=  x_end - 16
```

Since rafters are spaced 16 units apart:

```
R_last = R_0 + n * 16
```

where `n` is the number of rafter intervals that fit between `x_start` and `x_end`.

Substituting gives a second constraint on `R_0`:

```
x_end - 2  - n * 16  <=  R_0  <=  x_end - 16 - n * 16
```

The value of `n` is:

```
n = floor((x_end - x_start - 4) / 16)
```

The valid range for `R_0` is the intersection of:

```
[L_min, L_max]  =  [x_start + 2,        x_start + 16      ]
[P_min, P_max]  =  [x_end - 16 - n*16,  x_end - 2 - n*16  ]
```

So the feasible interval is:

```
[max(L_min, P_min(n)),  min(L_max, P_max(n))]
```

If this interval is empty, placement is impossible.
