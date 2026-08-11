from rayleigh.walker import collect_constraints


def test_walker_collects_operations():
    result = collect_constraints("distance = x\ntime = t\nspeed = distance / time\n")
    rendered = [c.equation_text() for c in result.constraints]
    assert len(rendered) >= 3
    assert any("var:speed" in item and "var:distance" in item for item in rendered)


def test_math_function_requires_dimensionless_input():
    result = collect_constraints("theta = theta0\ny = sin(theta)\n")
    assert any(c.message == "sin argument" for c in result.constraints)
