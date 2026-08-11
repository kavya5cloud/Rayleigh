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

# Ordered from specific to general.
PATTERNS: list[tuple[re.Pattern[str], Dimension, str]] = [
    (re.compile(r"(?:^|_)(?:mass|weight)(?:_kg)?$", re.I), _M, "mass name"),
    (re.compile(r"(?:^|_)(?:distance|length|radius|diameter|height|width|depth)(?:_m|_km|_cm)?$", re.I), _L, "length name"),
    (re.compile(r"(?:^|_)(?:dt|time|duration|period|t)(?:_s|_sec|_seconds)?$", re.I), _T, "time name"),
    (re.compile(r"(?:^|_)(?:velocity|speed)(?:_mps|_ms)?$", re.I), _L - _T, "velocity name"),
    (re.compile(r"(?:^|_)(?:acceleration|gravity)(?:_mps2)?$", re.I), _L - _T * 2, "acceleration name"),
    (re.compile(r"(?:^|_)(?:force)(?:_n)?$", re.I), _M + _L - _T * 2, "force name"),
    (re.compile(r"(?:^|_)(?:energy|work)(?:_j)?$", re.I), _M + _L * 2 - _T * 2, "energy name"),
    (re.compile(r"(?:^|_)(?:power)(?:_w)?$", re.I), _M + _L * 2 - _T * 3, "power name"),
    (re.compile(r"(?:^|_)(?:angle|theta|phi|radians?)$", re.I), _ZERO, "angle name"),
    (re.compile(r"(?:^|_)(?:current|amps?|amperage)(?:_a)?$", re.I), _I, "current name"),
    (re.compile(r"(?:^|_)(?:temperature|temp)(?:_k)?$", re.I), _TH, "temperature name"),
    (re.compile(r"(?:^|_)(?:amount|moles?|mol)$", re.I), _N, "amount name"),
    (re.compile(r"(?:^|_)(?:luminous|candela|intensity)(?:_cd)?$", re.I), _J, "luminous-intensity name"),
]


def infer_prior(name: str) -> tuple[Dimension, str] | None:
    for pattern, dimension, reason in PATTERNS:
        if pattern.search(name):
            return dimension, reason
    return None
