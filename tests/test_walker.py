from rayleigh.walker import collect_constraints


def test_walker_collects_operations():
    result = collect_constraints("distance = x\ntime = t\nspeed = distance / time\n")
    rendered = [c.equation_text() for c in result.constraints]
    assert len(rendered) >= 3
    assert any("var:speed" in item and "var:distance" in item for item in rendered)


def test_math_function_requires_dimensionless_input():
    result = collect_constraints("theta = theta0\ny = sin(theta)\n")
    assert any(c.message == "sin argument" for c in result.constraints)

def test_assignment_provenance_records_expression() -> None:
    result = collect_constraints(
        "distance = 100\n"
        "time = 5\n"
        "speed = distance / time\n"
    )

    speed_constraints = [
        c
        for c in result.constraints
        if c.message == "assignment to speed"
    ]

    assert speed_constraints

    constraint = speed_constraints[0]

    assert any(
        "speed =" in item
        for item in constraint.chain
    )


def test_prior_provenance_records_reason() -> None:
    result = collect_constraints(
        "distance = 100\n"
    )

    prior_constraints = [
        c
        for c in result.constraints
        if c.kind.value == "prior"
    ]

    assert prior_constraints

    constraint = prior_constraints[0]

    assert "distance" in constraint.chain[0]
    assert "reason:" in constraint.chain[1]

def test_speed_provenance_contains_expression() -> None:
    result = collect_constraints(
        "distance = 100\n"
        "time = 5\n"
        "speed = distance / time\n"
    )

    constraint = next(
        c
        for c in result.constraints
        if c.message == "assignment to speed"
    )

    assert "speed = distance / time" in constraint.chain


def test_force_provenance_contains_expression() -> None:
    result = collect_constraints(
        "mass = 10\n"
        "acceleration = 2\n"
        "force = mass * acceleration\n"
    )

    constraint = next(
        c
        for c in result.constraints
        if c.message == "assignment to force"
    )

    assert "force = mass * acceleration" in constraint.chain


def test_gravity_provenance_contains_expression() -> None:
    result = collect_constraints(
        "mass_1 = 5\n"
        "mass_2 = 10\n"
        "distance = 2\n"
        "force = 6.67430e-11 * mass_1 * mass_2 / distance**2\n"
    )

    constraint = next(
        c
        for c in result.constraints
        if c.message == "assignment to force"
    )

    assert (
        "force = 6.6743e-11 * mass_1 * mass_2 / distance ** 2"
        in constraint.chain
    )