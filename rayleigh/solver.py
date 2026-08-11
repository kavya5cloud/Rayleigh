from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import Iterable

from .constraints import Constraint
from .dimension import Dimension, DimensionExpr, BASE_DIMENSIONS


@dataclass(frozen=True)
class Finding:
    status: str  # consistent | contradiction | unknown
    line: int | None
    message: str
    left: str | None = None
    right: str | None = None
    chain: tuple[str, ...] = ()


@dataclass
class SolveResult:
    status: str
    assignments: dict[str, Dimension | None] = field(default_factory=dict)
    contradictions: list[Finding] = field(default_factory=list)
    unknowns: set[str] = field(default_factory=set)


def solve(constraints: list[Constraint]) -> SolveResult:
    variables = sorted({name for c in constraints for name in (*c.left.coefficients.keys(), *c.right.coefficients.keys())})
    if not variables:
        contradictions = _check_constant_constraints(constraints)
        return SolveResult(
            status="contradiction" if contradictions else "consistent",
            contradictions=contradictions,
        )

    # Each constraint gives one scalar linear equation per SI base dimension.
    values_by_variable: dict[str, list[Fraction | None]] = {v: [] for v in variables}
    solved_dimensions: dict[str, list[Fraction | None]] = {v: [None] * 7 for v in variables}
    contradictions: list[Finding] = []

    for dim_index, base_name in enumerate(BASE_DIMENSIONS):
        matrix: list[list[Fraction]] = []
        provenance: list[Constraint] = []
        for constraint in constraints:
            equation = _equation_row(constraint, dim_index, variables)
            if equation is None:
                continue
            coeffs, rhs = equation
            if all(c == 0 for c in coeffs):
                if rhs != 0:
                    contradictions.append(
                        Finding(
                            status="contradiction",
                            line=constraint.line,
                            message=f"inconsistent {base_name} exponent constraint",
                            left=constraint.left.format(),
                            right=constraint.right.format(),
                            chain=constraint.chain or (constraint.message,),
                        )
                    )
                continue
            matrix.append(coeffs + [rhs])
            provenance.append(constraint)

        solution, inconsistent_rows = _rref_solve(matrix)
        for row_index in inconsistent_rows:
            constraint = provenance[row_index]
            contradictions.append(
                Finding(
                    status="contradiction",
                    line=constraint.line,
                    message=f"constraints are inconsistent in {base_name}",
                    left=constraint.left.format(),
                    right=constraint.right.format(),
                    chain=constraint.chain or (constraint.message,),
                )
            )

        if solution is not None:
            for var_index, name in enumerate(variables):
                value = solution[var_index]
                if value is not None:
                    solved_dimensions[name][dim_index] = value

    if contradictions:
        return SolveResult(
            status="contradiction",
            assignments={name: _to_dimension(values) for name, values in solved_dimensions.items()},
            contradictions=_dedupe_findings(contradictions),
        )

    unknowns = {name for name, values in solved_dimensions.items() if any(value is None for value in values)}
    assignments = {name: _to_dimension(values) for name, values in solved_dimensions.items()}
    return SolveResult(
        status="unknown" if unknowns else "consistent",
        assignments=assignments,
        unknowns=unknowns,
    )


def _equation_row(constraint: Constraint, dim_index: int, variables: list[str]) -> tuple[list[Fraction], Fraction] | None:
    coeff_map = {name: Fraction(0) for name in variables}
    for name, coeff in constraint.left.coefficients.items():
        coeff_map[name] += coeff
    for name, coeff in constraint.right.coefficients.items():
        coeff_map[name] -= coeff
    constant_left = constraint.left.constant.exponents[dim_index]
    constant_right = constraint.right.constant.exponents[dim_index]
    # coeff*x + (left_const - right_const) = 0 => coeff*x = right_const - left_const
    rhs = constant_right - constant_left
    row = [coeff_map[name] for name in variables]
    return row, rhs


def _rref_solve(matrix: list[list[Fraction]]) -> tuple[list[Fraction | None] | None, list[int]]:
    if not matrix:
        return [None] * 0, []
    a = [row[:] for row in matrix]
    rows = len(a)
    cols = len(a[0]) - 1
    pivot_cols: dict[int, int] = {}
    pivot_row = 0
    inconsistent: list[int] = []

    for col in range(cols):
        pivot = next((r for r in range(pivot_row, rows) if a[r][col] != 0), None)
        if pivot is None:
            continue
        a[pivot_row], a[pivot] = a[pivot], a[pivot_row]
        divisor = a[pivot_row][col]
        a[pivot_row] = [value / divisor for value in a[pivot_row]]
        for r in range(rows):
            if r == pivot_row or a[r][col] == 0:
                continue
            factor = a[r][col]
            a[r] = [x - factor * y for x, y in zip(a[r], a[pivot_row])]
        pivot_cols[col] = pivot_row
        pivot_row += 1
        if pivot_row == rows:
            break

    for r, row in enumerate(a):
        if all(row[c] == 0 for c in range(cols)) and row[-1] != 0:
            inconsistent.append(r)

    if inconsistent:
        # Map RREF row indexes back to constraints only approximately; caller uses the original provenance row.
        return None, inconsistent

    solution: list[Fraction | None] = [None] * cols
    for col, row_index in pivot_cols.items():
        # A pivot variable is uniquely determined only if its row contains no free-variable terms.
        free_terms = [c for c in range(cols) if c != col and a[row_index][c] != 0]
        if not free_terms:
            solution[col] = a[row_index][-1]
    return solution, []


def _to_dimension(values: list[Fraction | None]) -> Dimension | None:
    if any(value is None for value in values):
        return None
    return Dimension(tuple(value for value in values if value is not None))


def _check_constant_constraints(constraints: list[Constraint]) -> list[Finding]:
    findings: list[Finding] = []
    for c in constraints:
        if not c.left.coefficients and not c.right.coefficients and c.left.constant != c.right.constant:
            findings.append(Finding("contradiction", c.line, c.message or "constant constraint is false", c.left.format(), c.right.format(), c.chain))
    return findings


def _dedupe_findings(findings: list[Finding]) -> list[Finding]:
    seen = set()
    result = []
    for finding in findings:
        key = (finding.line, finding.message, finding.left, finding.right)
        if key not in seen:
            seen.add(key)
            result.append(finding)
    return result
