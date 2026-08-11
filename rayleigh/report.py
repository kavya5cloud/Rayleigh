from __future__ import annotations

from .solver import SolveResult
from .walker import WalkResult


def render_constraints(result: WalkResult) -> str:
    lines: list[str] = []

    for constraint in result.constraints:
        lines.append(
            f"Line {constraint.line}: "
            f"{constraint.left.format()} = "
            f"{constraint.right.format()}"
        )

        if constraint.message:
            lines.append(f"  # {constraint.message}")

    return "\n".join(lines)


def render_result(
    result: SolveResult,
    source: str | None = None,
) -> str:
    lines: list[str] = []

    if result.status == "consistent":
        lines.append("✓ CONSISTENT")

    elif result.status == "contradiction":
        lines.append("✗ DIMENSIONAL CONTRADICTION")

    else:
        lines.append("? UNKNOWN")

    if result.contradictions:
        primary = next(
            (
                finding
                for finding in result.contradictions
                if "requires matching dimensions"
                in finding.message
            ),
            result.contradictions[0],
        )

        location = (
            f"Line {primary.line}"
            if primary.line is not None
            else "Unknown line"
        )

        lines.append("")
        lines.append(f"{location}: {primary.message}")

        # Show the actual source line when source was supplied.
        if source is not None and primary.line is not None:
            source_lines = source.splitlines()

            if 1 <= primary.line <= len(source_lines):
                lines.append("")
                lines.append(
                    f"    {source_lines[primary.line - 1].strip()}"
                )

        if primary.left is not None:
            lines.append("")
            lines.append(f"  Left:  {primary.left}")

        if primary.right is not None:
            lines.append(f"  Right: {primary.right}")

        if primary.chain:
            lines.append("")
            lines.append("  Constraint chain:")

            for item in primary.chain:
                lines.append(f"    → {item}")

    if result.unknowns:
        lines.append("")
        lines.append("Underdetermined variables:")

        for name in sorted(result.unknowns):
            lines.append(f"  ? {_clean_name(name)}")

    assigned = [
        (name, dimension)
        for name, dimension in result.assignments.items()
        if dimension is not None
    ]

    if assigned:
        lines.append("")
        lines.append("Inferred dimensions:")

        for name, dimension in sorted(assigned):
            assert dimension is not None

            lines.append(
                f"  {_clean_name(name):20s} → "
                f"{dimension.format()}"
            )

    return "\n".join(lines)


def _clean_name(name: str) -> str:
    if name.startswith("var:"):
        return name[4:]

    if name.startswith("const:"):
        return name[6:]

    return name