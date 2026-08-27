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
    walk: WalkResult | None = None,
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

    if walk is not None and assigned:
        evidence = _collect_evidence(
            walk,
            assigned_names={
                name
                for name, _ in assigned
            },
        )

        if evidence:
            lines.append("")
            lines.append("Evidence:")

            _render_evidence(
                lines,
                evidence,
                result,
            )

    return "\n".join(lines)


def _collect_evidence(
    walk: WalkResult,
    assigned_names: set[str],
) -> dict[str, list[str]]:
    """
    Build direct provenance for inferred variables.

    Assignment chains are kept as source-level expressions.
    Prior/constant evidence is also retained.
    """
    evidence: dict[str, list[str]] = {}

    for constraint in walk.constraints:
        target = _constraint_target(constraint)

        if target is None or target not in assigned_names:
            continue

        if not constraint.chain:
            continue

        entries = evidence.setdefault(target, [])

        for item in constraint.chain:
            if item not in entries:
                entries.append(item)

    return evidence


def _render_evidence(
    lines: list[str],
    evidence: dict[str, list[str]],
    result: SolveResult,
) -> None:
    """
    Render evidence recursively where assignment expressions reference
    other inferred variables.
    """
    rendered: set[str] = set()

    def render_variable(
        variable: str,
        indent: int,
        stack: set[str],
    ) -> None:
        if variable in stack:
            return

        if variable in rendered and indent > 1:
            return

        entries = evidence.get(variable)

        if not entries:
            return

        rendered.add(variable)

        prefix = " " * indent
        lines.append(
            f"{prefix}{_clean_name(variable)}"
        )

        next_stack = set(stack)
        next_stack.add(variable)

        for entry in entries:
            lines.append(
                f"{prefix}  → {entry}"
            )

            for dependency in _extract_variables(entry):
                dependency_key = f"var:{dependency}"

                if dependency_key in evidence:
                    render_variable(
                        dependency_key,
                        indent + 2,
                        next_stack,
                    )

    for name in sorted(evidence):
        render_variable(
            name,
            2,
            set(),
        )


def _extract_variables(text: str) -> list[str]:
    """
    Extract simple Python identifiers from a provenance expression.

    This intentionally stays lightweight. It is only used for recursively
    following source-level assignment expressions.
    """
    import ast

    try:
        tree = ast.parse(
            text.split("=", 1)[1].strip(),
            mode="eval",
        )
    except (SyntaxError, IndexError):
        return []

    names: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            if node.id not in names:
                names.append(node.id)

    return names


def _constraint_target(constraint) -> str | None:
    for name in constraint.left.coefficients:
        if name.startswith("var:"):
            return name

    return None


def _clean_name(name: str) -> str:
    if name.startswith("var:"):
        return name[4:]

    if name.startswith("const:"):
        return name[6:]

    return name

def build_provenance(
    walk: WalkResult,
    result: SolveResult,
) -> list[dict[str, object]]:
    """
    Build structured provenance for all successfully inferred variables.
    """

    assigned_names = {
        name
        for name, dimension in result.assignments.items()
        if dimension is not None
    }

    evidence = _collect_evidence(
        walk,
        assigned_names=assigned_names,
    )

    def build_node(
        variable: str,
        stack: set[str],
    ) -> dict[str, object] | None:
        if variable in stack:
            return None

        entries = evidence.get(variable)
        dimension = result.assignments.get(variable)

        if dimension is None:
            return None

        node: dict[str, object] = {
            "variable": _clean_name(variable),
            "dimension": dimension.format(),
            "evidence": [],
        }

        next_stack = set(stack)
        next_stack.add(variable)

        evidence_items: list[dict[str, object]] = []

        for entry in entries or []:
            item: dict[str, object] = {
                "text": entry,
            }

            dependencies: list[dict[str, object]] = []

            for dependency in _extract_variables(entry):
                dependency_key = f"var:{dependency}"

                if dependency_key not in evidence:
                    continue

                child = build_node(
                    dependency_key,
                    next_stack,
                )

                if child is not None:
                    dependencies.append(child)

            if dependencies:
                item["dependencies"] = dependencies

            evidence_items.append(item)

        node["evidence"] = evidence_items

        return node

    provenance: list[dict[str, object]] = []

    for variable in sorted(
        assigned_names,
        key=_clean_name,
    ):
        node = build_node(
            variable,
            set(),
        )

        if node is not None:
            provenance.append(node)

    return provenance

def render_diagnostics(
    result: SolveResult,
    filename: str,
) -> str:
    """
    Render concise editor-friendly diagnostics.

    Prefer the primary dimensional mismatch and suppress
    downstream solver consequences.
    """

    if not result.contradictions:
        return ""

    primary = next(
        (
            finding
            for finding in result.contradictions
            if finding.kind == "dimension_mismatch"
        ),
        result.contradictions[0],
    )

    line = primary.line or 1

    column = (
        primary.column + 1
        if primary.column is not None
        else 1
    )

    code = primary.kind or "solver_contradiction"
    severity = primary.severity or "error"

    return (
        f"{filename}:{line}:{column}: "
        f"{severity}[{code}]: "
        f"{primary.message}"
    )