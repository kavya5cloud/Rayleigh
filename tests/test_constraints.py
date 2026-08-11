from rayleigh.constraints import Constraint, ConstraintKind
from rayleigh.dimension import DimensionExpr


def test_constraint_creation() -> None:
    left = DimensionExpr.unknown("speed")
    right = DimensionExpr.unknown("distance")

    constraint = Constraint(
        left=left,
        right=right,
        line=10,
        kind=ConstraintKind.EQUALITY,
        message="division",
    )

    assert constraint.left == left
    assert constraint.right == right
    assert constraint.line == 10
    assert constraint.kind == ConstraintKind.EQUALITY
    assert constraint.message == "division"


def test_constraint_equation_text() -> None:
    left = DimensionExpr.unknown("speed")
    right = DimensionExpr.unknown("distance")

    constraint = Constraint(
        left=left,
        right=right,
        line=10,
    )

    assert constraint.equation_text() == "speed = distance"