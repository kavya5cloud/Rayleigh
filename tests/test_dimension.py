from rayleigh.dimension import (
    ACCELERATION,
    AREA,
    DIMENSIONLESS,
    ENERGY,
    FORCE,
    LENGTH,
    MASS,
    TIME,
    VELOCITY,
    VOLUME,
)


def test_length() -> None:
    assert LENGTH.exponents == (
        0, 1, 0, 0, 0, 0, 0
    )


def test_velocity() -> None:
    assert VELOCITY.exponents == (
        0, 1, -1, 0, 0, 0, 0
    )


def test_acceleration() -> None:
    assert ACCELERATION.exponents == (
        0, 1, -2, 0, 0, 0, 0
    )


def test_force() -> None:
    assert FORCE == MASS.multiply(ACCELERATION)


def test_energy() -> None:
    assert ENERGY == FORCE.multiply(LENGTH)


def test_area() -> None:
    assert AREA == LENGTH.power(2)


def test_volume() -> None:
    assert VOLUME == LENGTH.power(3)


def test_dimensionless() -> None:
    assert DIMENSIONLESS.is_dimensionless()


def test_multiplication() -> None:
    result = LENGTH.multiply(LENGTH)

    assert result.exponents == (
        0, 2, 0, 0, 0, 0, 0
    )


def test_division() -> None:
    result = LENGTH.divide(TIME)

    assert result == VELOCITY


def test_power() -> None:
    result = LENGTH.power(2)

    assert result == AREA


def test_string_velocity() -> None:
    assert str(VELOCITY) == "L T^-1"


def test_string_acceleration() -> None:
    assert str(ACCELERATION) == "L T^-2"


def test_string_energy() -> None:
    assert str(ENERGY) == "M L^2 T^-2"