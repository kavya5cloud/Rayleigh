from rayleigh.solver import solve
from rayleigh.walker import collect_constraints


def test_clean_case_is_consistent():
    source = """
distance = radius
radius = 10
velocity = distance / dt
"""
    result = solve(collect_constraints(source).constraints)
    assert result.status in {"consistent", "unknown"}


def test_dimensionally_inconsistent_addition():
    source = """
distance_m = 10
velocity = distance_m / dt
y = velocity + 9.81
"""
    result = solve(collect_constraints(source).constraints)
    assert result.status == "contradiction"


def test_underdetermined_variable_is_unknown():
    source = "x = y\n"
    result = solve(collect_constraints(source).constraints)
    assert result.status == "unknown"
    assert {"var:x", "var:y"}.issubset(result.unknowns)


def test_ten_is_not_mistaken_for_standard_gravity():
    result = collect_constraints("radius_m = 10\n")
    assert not any("recognized constant" in c.message for c in result.constraints)
