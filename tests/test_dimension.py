from fractions import Fraction

from rayleigh.dimension import Dimension, DimensionExpr


def test_dimension_algebra():
    length = Dimension.basis(1)
    time = Dimension.basis(2)
    velocity = length - time
    assert velocity.exponents == (0, 1, -1, 0, 0, 0, 0)


def test_dimension_expr_linear_algebra():
    x = DimensionExpr.unknown("x")
    y = DimensionExpr.unknown("y")
    expr = (x + y).scale(Fraction(2)) - y
    assert expr.coefficients["x"] == 2
    assert expr.coefficients["y"] == 1
