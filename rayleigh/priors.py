from __future__ import annotations

import re

from .dimension import Dimension


_ZERO = Dimension.zero()
_M = Dimension.basis(0)
_L = Dimension.basis(1)
_T = Dimension.basis(2)
_I = Dimension.basis(3)
_TH = Dimension.basis(4)
_N = Dimension.basis(5)
_J = Dimension.basis(6)


PATTERNS: list[tuple[re.Pattern[str], Dimension, str]] = [
    # Mass
    (
        re.compile(
            r"^(?:mass|weight)(?:_\d+)?(?:_kg)?$",
            re.I,
        ),
        _M,
        "mass name",
    ),

    # Area
    (
        re.compile(
            r"^area(?:_\d+)?(?:_m2|_km2|_cm2)?$",
            re.I,
        ),
        _L * 2,
        "area name",
    ),

    # Volume
    (
        re.compile(
            r"^volume(?:_\d+)?(?:_m3|_km3|_cm3)?$",
            re.I,
        ),
        _L * 3,
        "volume name",
    ),
    # Displacement
    (
        re.compile(
            r"^displacement(?:_\d+)?(?:_m|_cm|_mm)?$",
            re.I,
        ),
        _L,
        "displacement name",
    ),

    # Spring constant
    (
        re.compile(
            r"^spring_constant(?:_\d+)?(?:_n_m)?$",
            re.I,
        ),
        _M - (_T * 2),
        "spring-constant name",
    ),

        # Pressure
    (
        re.compile(
            r"^pressure(?:_\d+)?(?:_pa|_kpa|_bar)?$",
            re.I,
        ),
        _M - _L - (_T * 2),
        "pressure name",
    ),

    # Specific heat capacity
    (
        re.compile(
            r"^specific_heat(?:_\d+)?(?:_j_kg_k)?$",
            re.I,
        ),
        (_L * 2) - (_T * 2) - _TH,
        "specific-heat name",
    ),

    # Temperature change
    (
        re.compile(
            r"^(?:temperature_change|delta_t)(?:_\d+)?(?:_k)?$",
            re.I,
        ),
        _TH,
        "temperature-change name",
    ),
    
    # Length
    (
        re.compile(
            r"^(?:distance|length|radius|diameter|height|width|depth)"
            r"(?:_\d+)?(?:_m|_km|_cm)?$",
            re.I,
        ),
        _L,
        "length name",
    ),

    # Time
    (
        re.compile(
            r"^(?:dt|time|duration|period|t)"
            r"(?:_\d+)?(?:_s|_sec|_seconds)?$",
            re.I,
        ),
        _T,
        "time name",
    ),

    # Velocity
    (
        re.compile(
            r"^(?:velocity|speed)(?:_\d+)?(?:_mps|_ms)?$",
            re.I,
        ),
        _L - _T,
        "velocity name",
    ),

    # Acceleration
    (
        re.compile(
            r"^(?:acceleration|gravity)"
            r"(?:_\d+)?(?:_mps2)?$",
            re.I,
        ),
        _L - (_T * 2),
        "acceleration name",
    ),

    # Force
    (
        re.compile(
            r"^force(?:_\d+)?(?:_n)?$",
            re.I,
        ),
        _M + _L - (_T * 2),
        "force name",
    ),

    # Energy / Work
    (
        re.compile(
            r"^(?:energy|work)"
            r"(?:_\d+)?(?:_j)?$",
            re.I,
        ),
        _M + (_L * 2) - (_T * 2),
        "energy name",
    ),

    # Power
    (
        re.compile(
            r"^power(?:_\d+)?(?:_w)?$",
            re.I,
        ),
        _M + (_L * 2) - (_T * 3),
        "power name",
    ),

    # Dimensionless angles
    (
        re.compile(
            r"^(?:angle|theta|phi|radians?)(?:_\d+)?$",
            re.I,
        ),
        _ZERO,
        "angle name",
    ),

    # Electric current
    (
        re.compile(
            r"^(?:current|amps?|amperage)"
            r"(?:_\d+)?(?:_a)?$",
            re.I,
        ),
        _I,
        "current name",
    ),

    # Temperature
    (
        re.compile(
            r"^(?:temperature|temp)"
            r"(?:_\d+)?(?:_k)?$",
            re.I,
        ),
        _TH,
        "temperature name",
    ),

    # Amount of substance
    (
        re.compile(
            r"^(?:amount|moles?|mol)(?:_\d+)?$",
            re.I,
        ),
        _N,
        "amount name",
    ),

    # Luminous intensity
    (
        re.compile(
            r"^(?:luminous|candela|intensity)"
            r"(?:_\d+)?(?:_cd)?$",
            re.I,
        ),
        _J,
        "luminous-intensity name",
    ),
]


def infer_prior(name: str) -> tuple[Dimension, str] | None:
    """Infer a likely physical dimension from a variable name."""

    for pattern, dimension, reason in PATTERNS:
        if pattern.fullmatch(name):
            return dimension, reason

    return None