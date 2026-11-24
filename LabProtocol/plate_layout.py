import math


def _row_label(index):
    label = ""
    while index >= 0:
        index, remainder = divmod(index, 26)
        label = chr(65 + remainder) + label
        index -= 1
    return label


def build_plate_layout(
    experimental_groups,
    rows,
    columns,
    container_label="Plate",
    position_prefix=None
):
    """Assign group replicates to a row-major series of reusable vessel grids."""
    if not isinstance(rows, int) or rows < 1:
        raise ValueError("Layout rows must be a positive whole number.")
    if not isinstance(columns, int) or columns < 1:
        raise ValueError("Layout columns must be a positive whole number.")

    capacity = rows * columns
    assignments = []
    for group_index, group in enumerate(experimental_groups):
        replicates = group.get("technical_replicates")
        if not isinstance(replicates, int) or replicates < 1:
            raise ValueError(
                f"Experimental group {group_index + 1} must have a positive "
                "whole-number replicate count."
            )
        for replicate in range(1, replicates + 1):
            assignments.append({
                "strain": group["strain"],
                "treatment": group["treatment"],
                "replicate": replicate
            })

    vessel_count = len(assignments)
    container_count = math.ceil(vessel_count / capacity)
    layouts = []
    for container_index in range(container_count):
        positions = []
        for row_index in range(rows):
            position_row = []
            for column_index in range(columns):
                assignment_index = (
                    container_index * capacity
                    + row_index * columns
                    + column_index
                )
                position = (
                    f"{position_prefix} {assignment_index + 1}"
                    if position_prefix
                    else f"{_row_label(row_index)}{column_index + 1}"
                )
                assignment = (
                    assignments[assignment_index]
                    if assignment_index < vessel_count
                    else None
                )
                position_row.append({
                    "position": position,
                    "strain": assignment["strain"] if assignment else None,
                    "treatment": (
                        assignment["treatment"] if assignment else None
                    ),
                    "replicate": (
                        assignment["replicate"] if assignment else None
                    )
                })
            positions.append(position_row)
        layouts.append({
            "label": f"{container_label} {container_index + 1}",
            "rows": positions,
            "row_count": rows,
            "column_count": columns
        })
    return layouts
