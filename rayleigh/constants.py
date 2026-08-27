from __future__ import annotations

from dataclasses import dataclass
from math import isclose

from .dimension import Dimension


@dataclass(frozen=True)
class ConstantFingerprint:
    value: float
    dimension: Dimension
    tolerance: float = 1e-6
    name: str = ""


M = Dimension.basis(0)
L = Dimension.basis(1)
T = Dimension.basis(2)
I = Dimension.basis(3)
TH = Dimension.basis(4)
N = Dimension.basis(5)
J = Dimension.basis(6)


CONSTANTS = [
    ConstantFingerprint(
        9.80665,
        Dimension((0, 1, -2, 0, 0, 0, 0)),
        0.001,
        "standard_gravity",
    ),
    ConstantFingerprint(
        299792458.0,
        L - T,
        1e-6,
        "speed_of_light",
    ),
    ConstantFingerprint(
        6.67430e-11,
        Dimension((-1, 3, -2, 0, 0, 0, 0)),
        5e-5,
        "gravitational_constant",
    ),
    ConstantFingerprint(
        8.9875517923e9,
        Dimension((1, 3, -4, -2, 0, 0, 0)),
        5e-5,
        "coulomb_constant",
    ),
    ConstantFingerprint(
        1.380649e-23,
        Dimension((1, 2, -2, 0, -1, 0, 0)),
        5e-5,
        "boltzmann_constant",
    ),
    ConstantFingerprint(
        6.62607015e-34,
        Dimension((1, 2, -1, 0, 0, 0, 0)),
        5e-5,
        "planck_constant",
    ),
]


def match_constant(value: float) -> ConstantFingerprint | None:
    if value == 0:
        return None

    for fingerprint in CONSTANTS:
        if isclose(
            abs(value),
            abs(fingerprint.value),
            rel_tol=fingerprint.tolerance,
            abs_tol=0.0,
        ):
            return fingerprint

    return None