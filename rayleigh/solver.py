from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction

from .constraints import Constraint
from .dimension import Dimension, BASE_DIMENSIONS


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
    """
    Solve dimensional constraints across the seven SI base dimensions.
    """

    variables = sorted(
        {
            name
            for constraint in constraints
            for name in (
                *constraint.left.coefficients.keys(),
                *constraint.right.coefficients.keys(),
            )
        }
    )

    # No symbolic variables: only concrete constraints remain.
    if not variables:
        contradictions = _check_constant_constraints(constraints)

        return SolveResult(
            status="contradiction" if contradictions else "consistent",
            contradictions=contradictions,
        )

    solved_dimensions: dict[str, list[Fraction | None]] = {
        name: [None] * len(BASE_DIMENSIONS)
        for name in variables
    }

    contradictions: list[Finding] = []

    # Solve each SI base dimension independently.
    for dim_index, base_name in enumerate(BASE_DIMENSIONS):
        matrix: list[list[Fraction]] = []
        provenance: list[Constraint] = []

        for constraint in constraints:
            coeffs, rhs = _equation_row(
                constraint,
                dim_index,
                variables,
            )

            # Pure constant equation.
            if all(value == 0 for value in coeffs):
                if rhs != 0:
                    contradictions.append(
                        Finding(
                            status="contradiction",
                            line=constraint.line,
                            message=(
                                f"inconsistent {base_name} "
                                "exponent constraint"
                            ),
                            left=constraint.left.format(),
                            right=constraint.right.format(),
                            chain=(
                                constraint.chain
                                or (constraint.message,)
                            ),
                        )
                    )
                continue

            matrix.append(coeffs + [rhs])
            provenance.append(constraint)

        solution, inconsistent_rows = _rref_solve(matrix)

        # Record contradictions while preserving original row provenance.
        for row_index in inconsistent_rows:
            if 0 <= row_index < len(provenance):
                constraint = provenance[row_index]

                contradictions.append(
                    Finding(
                        status="contradiction",
                        line=constraint.line,
                        message=(
                            f"constraints are inconsistent "
                            f"in {base_name}"
                        ),
                        left=constraint.left.format(),
                        right=constraint.right.format(),
                        chain=(
                            constraint.chain
                            or (constraint.message,)
                        ),
                    )
                )

        # Preserve dimensions that can still be solved.
        if solution is not None:
            for variable_index, name in enumerate(variables):
                value = solution[variable_index]

                if value is not None:
                    solved_dimensions[name][dim_index] = value

    # ------------------------------------------------------------
    # Contradiction handling
    # ------------------------------------------------------------

    if contradictions:
        operation_conflicts = _find_operation_conflicts(
            constraints
        )

        suspects = _find_suspect_constraints(
            constraints
        )

        contradictions = (
            operation_conflicts
            + suspects
            + contradictions
        )

        return SolveResult(
            status="contradiction",
            assignments={
                name: _to_dimension(values)
                for name, values in solved_dimensions.items()
            },
            contradictions=_dedupe_findings(
                contradictions
            ),
        )

    # ------------------------------------------------------------
    # Unknown / consistent handling
    # ------------------------------------------------------------

    unknowns = {
        name
        for name, values in solved_dimensions.items()
        if any(value is None for value in values)
    }

    assignments = {
        name: _to_dimension(values)
        for name, values in solved_dimensions.items()
    }

    return SolveResult(
        status="unknown" if unknowns else "consistent",
        assignments=assignments,
        unknowns=unknowns,
    )


def _find_suspect_constraints(
    constraints: list[Constraint],
) -> list[Finding]:
    """
    Identify constraints whose removal restores consistency.

    This is a diagnostic heuristic, not proof of blame.
    """

    findings: list[Finding] = []

    for index, constraint in enumerate(constraints):
        remaining = (
            constraints[:index]
            + constraints[index + 1:]
        )

        if not remaining:
            continue

        if not _constraints_are_consistent(remaining):
            continue

        findings.append(
            Finding(
                status="contradiction",
                line=constraint.line,
                message="likely source of dimensional contradiction",
                left=constraint.left.format(),
                right=constraint.right.format(),
                chain=(
                    constraint.chain
                    or (constraint.message,)
                ),
            )
        )

    return findings


def _constraints_are_consistent(
    constraints: list[Constraint],
) -> bool:
    """
    Return True if the complete constraint system is consistent.
    """

    variables = sorted(
        {
            name
            for constraint in constraints
            for name in (
                *constraint.left.coefficients.keys(),
                *constraint.right.coefficients.keys(),
            )
        }
    )

    if not variables:
        return not bool(
            _check_constant_constraints(constraints)
        )

    for dim_index in range(len(BASE_DIMENSIONS)):
        matrix: list[list[Fraction]] = []

        for constraint in constraints:
            coeffs, rhs = _equation_row(
                constraint,
                dim_index,
                variables,
            )

            if all(value == 0 for value in coeffs):
                if rhs != 0:
                    return False
                continue

            matrix.append(coeffs + [rhs])

        _, inconsistent_rows = _rref_solve(matrix)

        if inconsistent_rows:
            return False

    return True


def _equation_row(
    constraint: Constraint,
    dim_index: int,
    variables: list[str],
) -> tuple[list[Fraction], Fraction]:
    """
    Convert:

        left == right

    into:

        A*x = b
    """

    coeff_map = {
        name: Fraction(0)
        for name in variables
    }

    for name, coefficient in constraint.left.coefficients.items():
        coeff_map[name] += coefficient

    for name, coefficient in constraint.right.coefficients.items():
        coeff_map[name] -= coefficient

    left_constant = constraint.left.constant.exponents[dim_index]
    right_constant = constraint.right.constant.exponents[dim_index]

    rhs = right_constant - left_constant

    row = [
        coeff_map[name]
        for name in variables
    ]

    return row, rhs


def _rref_solve(
    matrix: list[list[Fraction]],
) -> tuple[list[Fraction | None] | None, list[int]]:
    """
    Solve a linear system using exact RREF.

    Provenance is stored separately from the arithmetic matrix so
    row operations cannot corrupt original row indexes.
    """

    if not matrix:
        return [None] * 0, []

    rows = [
        {
            "values": row[:],
            "source": index,
        }
        for index, row in enumerate(matrix)
    ]

    row_count = len(rows)
    variable_count = len(matrix[0]) - 1

    pivot_row = 0
    pivot_columns: dict[int, int] = {}

    for column in range(variable_count):
        pivot = next(
            (
                row
                for row in range(pivot_row, row_count)
                if rows[row]["values"][column] != 0
            ),
            None,
        )

        if pivot is None:
            continue

        rows[pivot_row], rows[pivot] = (
            rows[pivot],
            rows[pivot_row],
        )

        values = rows[pivot_row]["values"]
        divisor = values[column]

        rows[pivot_row]["values"] = [
            value / divisor
            for value in values
        ]

        for row in range(row_count):
            if row == pivot_row:
                continue

            current = rows[row]["values"]
            factor = current[column]

            if factor == 0:
                continue

            pivot_values = rows[pivot_row]["values"]

            rows[row]["values"] = [
                current_value - factor * pivot_value
                for current_value, pivot_value in zip(
                    current,
                    pivot_values,
                )
            ]

        pivot_columns[column] = pivot_row
        pivot_row += 1

        if pivot_row == row_count:
            break

    # ------------------------------------------------------------
    # Contradictions
    # ------------------------------------------------------------

    inconsistent_rows: list[int] = []

    for row in rows:
        values = row["values"]

        coefficients = values[:variable_count]
        rhs = values[variable_count]

        if (
            all(value == 0 for value in coefficients)
            and rhs != 0
        ):
            inconsistent_rows.append(
                row["source"]
            )

    if inconsistent_rows:
        return None, inconsistent_rows

    # ------------------------------------------------------------
    # Unique solutions
    # ------------------------------------------------------------

    solution: list[Fraction | None] = [
        None
    ] * variable_count

    for column, row_index in pivot_columns.items():
        values = rows[row_index]["values"]

        has_free_terms = any(
            other_column != column
            and values[other_column] != 0
            for other_column in range(variable_count)
        )

        if not has_free_terms:
            solution[column] = values[variable_count]

    return solution, []


def _find_operation_conflicts(
    constraints: list[Constraint],
) -> list[Finding]:
    """
    Identify direct dimensional conflicts in operations such as
    addition, subtraction, modulo, and comparisons.
    """

    findings: list[Finding] = []

    operation_messages = {
        "addition/subtraction",
        "modulo",
        "comparison",
        "conditional expression",
    }

    for index, constraint in enumerate(constraints):
        if constraint.message not in operation_messages:
            continue

        context = [
            other
            for other_index, other in enumerate(constraints)
            if other_index != index
            and not other.message.startswith("assignment to ")
        ]

        left_dimension = _infer_expression_dimension(
            constraint.left,
            context,
        )

        right_dimension = _infer_expression_dimension(
            constraint.right,
            context,
        )

        if (
            left_dimension is not None
            and right_dimension is not None
            and left_dimension != right_dimension
        ):
            findings.append(
                Finding(
                    status="contradiction",
                    line=constraint.line,
                    message=(
                        f"{constraint.message} requires "
                        "matching dimensions"
                    ),
                    left=left_dimension.format(),
                    right=right_dimension.format(),
                    chain=(
                        constraint.chain
                        or (constraint.message,)
                    ),
                )
            )

    return findings


def _infer_expression_dimension(
    expression,
    context: list[Constraint],
) -> Dimension | None:
    """
    Infer a concrete dimension for a symbolic expression.

    Returns None when the available constraints are insufficient.
    """

    variables = sorted(
        {
            name
            for constraint in context
            for name in (
                *constraint.left.coefficients.keys(),
                *constraint.right.coefficients.keys(),
            )
        }
    )

    if not expression.coefficients:
        return expression.constant

    if not variables:
        return None

    values: dict[str, list[Fraction | None]] = {
        name: [None] * len(BASE_DIMENSIONS)
        for name in variables
    }

    for dim_index in range(len(BASE_DIMENSIONS)):
        matrix: list[list[Fraction]] = []

        for constraint in context:
            coeffs, rhs = _equation_row(
                constraint,
                dim_index,
                variables,
            )

            if all(value == 0 for value in coeffs):
                if rhs != 0:
                    return None
                continue

            matrix.append(coeffs + [rhs])

        solution, inconsistent_rows = _rref_solve(matrix)

        if inconsistent_rows or solution is None:
            return None

        for index, name in enumerate(variables):
            if solution[index] is not None:
                values[name][dim_index] = solution[index]

    result = expression.constant

    for name, coefficient in expression.coefficients.items():
        dimension_values = values.get(name)

        if dimension_values is None:
            return None

        if any(value is None for value in dimension_values):
            return None

        dimension = Dimension(
            tuple(
                value
                for value in dimension_values
                if value is not None
            )
        )

        result = result + dimension * coefficient

    return result


def _to_dimension(
    values: list[Fraction | None],
) -> Dimension | None:
    """
    Convert seven solved exponents into a concrete Dimension.
    """

    if any(value is None for value in values):
        return None

    return Dimension(
        tuple(
            value
            for value in values
            if value is not None
        )
    )


def _check_constant_constraints(
    constraints: list[Constraint],
) -> list[Finding]:
    """
    Check constraints containing only concrete dimensions.
    """

    findings: list[Finding] = []

    for constraint in constraints:
        if (
            not constraint.left.coefficients
            and not constraint.right.coefficients
            and constraint.left.constant
            != constraint.right.constant
        ):
            findings.append(
                Finding(
                    status="contradiction",
                    line=constraint.line,
                    message=(
                        constraint.message
                        or "constant constraint is false"
                    ),
                    left=constraint.left.format(),
                    right=constraint.right.format(),
                    chain=constraint.chain,
                )
            )

    return findings


def _dedupe_findings(
    findings: list[Finding],
) -> list[Finding]:
    """
    Remove duplicate findings while preserving order.
    """

    seen: set[
        tuple[
            int | None,
            str,
            str | None,
            str | None,
        ]
    ] = set()

    result: list[Finding] = []

    for finding in findings:
        key = (
            finding.line,
            finding.message,
            finding.left,
            finding.right,
        )

        if key in seen:
            continue

        seen.add(key)
        result.append(finding)

    return result