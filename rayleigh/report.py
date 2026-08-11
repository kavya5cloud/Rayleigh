from __future__ import annotations

from .dimension import Dimension
from .solver import SolveResult
from .walker import WalkResult


def render_constraints(result: WalkResult) -> str:
    lines: list[str] = []
    for constraint in result.constraints:
        lines.append(f"Line {constraint.line}: {constraint.left} = {constraint.right}")
        if constraint.message:
            lines.append(f"  # {constraint.message}")
    return "\n".join(lines)


def render_result(result: SolveResult) -> str:
    lines: list[str] = []
    if result.status == "consistent":
        lines.append("✓ CONSISTENT")
    elif result.status == "contradiction":
        lines.append("✗ CONTRADICTION")
        for finding in result.contradictions:
            location = f"Line {finding.line}" if finding.line else "Unknown line"
            lines.append(f"\n{location}: {finding.message}")
            if finding.left is not None and finding.right is not None:
                lines.append(f"  {finding.left} ≠ {finding.right}")
            if finding.chain:
                lines.append("  Constraint chain:")
                for item in finding.chain:
                    lines.append(f"    → {item}")
    else:
        lines.append("? UNKNOWN")
        if result.unknowns:
            lines.append("\nUnderdetermined variables:")
            for name in sorted(result.unknowns):
                lines.append(f"  ? {name}")

    assigned = [(name, dim) for name, dim in result.assignments.items() if dim is not None]
    if assigned:
        lines.append("\nInferred dimensions:")
        for name, dim in sorted(assigned):
            assert dim is not None
            lines.append(f"  {name:20s} → {dim.format()}")
    return "\n".join(lines)
