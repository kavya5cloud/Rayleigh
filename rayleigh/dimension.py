from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import Mapping


BASE_DIMENSIONS = (
    "M",
    "L",
    "T",
    "I",
    "Θ",
    "N",
    "J",
)

ZERO_VECTOR = (Fraction(0),) * 7


@dataclass(frozen=True)
class Dimension:
    """Concrete SI dimensional fingerprint represented by seven exponents."""

    exponents: tuple[Fraction, ...]

    def __post_init__(self) -> None:
        if len(self.exponents) != 7:
            raise ValueError(
                "A dimension must contain exactly 7 exponents"
            )

        object.__setattr__(
            self,
            "exponents",
            tuple(Fraction(x) for x in self.exponents),
        )

    @classmethod
    def zero(cls) -> "Dimension":
        return cls(ZERO_VECTOR)

    @classmethod
    def basis(cls, index: int) -> "Dimension":
        values = list(ZERO_VECTOR)
        values[index] = Fraction(1)
        return cls(tuple(values))

    def __add__(self, other: "Dimension") -> "Dimension":
        return Dimension(
            tuple(
                a + b
                for a, b in zip(
                    self.exponents,
                    other.exponents,
                )
            )
        )

    def __sub__(self, other: "Dimension") -> "Dimension":
        return Dimension(
            tuple(
                a - b
                for a, b in zip(
                    self.exponents,
                    other.exponents,
                )
            )
        )

    def __mul__(
        self,
        scalar: int | Fraction,
    ) -> "Dimension":
        scalar = Fraction(scalar)

        return Dimension(
            tuple(
                x * scalar
                for x in self.exponents
            )
        )

    def __neg__(self) -> "Dimension":
        return self * -1

    def multiply(self, other: "Dimension") -> "Dimension":
        """Multiply two physical dimensions."""
        return self + other

    def divide(self, other: "Dimension") -> "Dimension":
        """Divide one physical dimension by another."""
        return self - other

    def power(
        self,
        exponent: int | Fraction,
    ) -> "Dimension":
        """Raise a physical dimension to a rational power."""
        return self * Fraction(exponent)

    def is_dimensionless(self) -> bool:
        return self.exponents == ZERO_VECTOR

    def format(self) -> str:
        if self.is_dimensionless():
            return "1"

        parts: list[str] = []

        for name, exp in zip(
            BASE_DIMENSIONS,
            self.exponents,
        ):
            if exp == 0:
                continue

            if exp.denominator == 1:
                exponent = str(exp.numerator)
            else:
                exponent = (
                    f"{exp.numerator}/{exp.denominator}"
                )

            parts.append(
                name
                if exp == 1
                else f"{name}^{exponent}"
            )

        return " ".join(parts)

    def __str__(self) -> str:
        return self.format()


# ------------------------------------------------------------------
# Named base / derived dimensions
# ------------------------------------------------------------------

MASS = Dimension.basis(0)
LENGTH = Dimension.basis(1)
TIME = Dimension.basis(2)
CURRENT = Dimension.basis(3)
TEMPERATURE = Dimension.basis(4)
AMOUNT = Dimension.basis(5)
LUMINOUS_INTENSITY = Dimension.basis(6)

DIMENSIONLESS = Dimension.zero()

AREA = LENGTH.power(2)
VOLUME = LENGTH.power(3)

VELOCITY = LENGTH.divide(TIME)
ACCELERATION = LENGTH.divide(TIME.power(2))

FORCE = MASS.multiply(ACCELERATION)
ENERGY = FORCE.multiply(LENGTH)
POWER = ENERGY.divide(TIME)

MOMENTUM = MASS.multiply(VELOCITY)
DENSITY = MASS.divide(VOLUME)
PRESSURE = FORCE.divide(AREA)


@dataclass(frozen=True)
class DimensionExpr:
    """Affine expression in unknown variable dimensions."""

    constant: Dimension = field(
        default_factory=Dimension.zero
    )

    coefficients: Mapping[str, Fraction] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        cleaned = {
            key: Fraction(value)
            for key, value in self.coefficients.items()
            if Fraction(value) != 0
        }

        object.__setattr__(
            self,
            "coefficients",
            cleaned,
        )

    @classmethod
    def unknown(
        cls,
        name: str,
    ) -> "DimensionExpr":
        return cls(
            coefficients={
                name: Fraction(1),
            }
        )

    @classmethod
    def concrete(
        cls,
        dimension: Dimension,
    ) -> "DimensionExpr":
        return cls(
            constant=dimension,
        )

    @classmethod
    def dimensionless(cls) -> "DimensionExpr":
        return cls.concrete(
            Dimension.zero()
        )

    def __add__(
        self,
        other: "DimensionExpr",
    ) -> "DimensionExpr":
        coefficients = dict(
            self.coefficients
        )

        for name, value in other.coefficients.items():
            coefficients[name] = (
                coefficients.get(
                    name,
                    Fraction(0),
                )
                + value
            )

        return DimensionExpr(
            self.constant + other.constant,
            coefficients,
        )

    def __sub__(
        self,
        other: "DimensionExpr",
    ) -> "DimensionExpr":
        return self + (-other)

    def __neg__(self) -> "DimensionExpr":
        return DimensionExpr(
            -self.constant,
            {
                key: -value
                for key, value
                in self.coefficients.items()
            },
        )

    def scale(
        self,
        scalar: int | Fraction,
    ) -> "DimensionExpr":
        scalar = Fraction(scalar)

        return DimensionExpr(
            self.constant * scalar,
            {
                key: value * scalar
                for key, value
                in self.coefficients.items()
            },
        )

    def format(self) -> str:
        terms: list[str] = []

        if not self.constant.is_dimensionless():
            terms.append(
                self.constant.format()
            )

        for name, coeff in sorted(
            self.coefficients.items()
        ):
            coeff_text = (
                ""
                if coeff == 1
                else (
                    "-"
                    if coeff == -1
                    else f"{coeff}*"
                )
            )

            terms.append(
                f"{coeff_text}{name}"
            )

        return (
            " + ".join(terms)
            if terms
            else "1"
        )

    def __str__(self) -> str:
        return self.format()