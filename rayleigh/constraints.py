from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .dimension import DimensionExpr


class ConstraintKind(str, Enum):
    EQUALITY = "equality"
    DIMENSIONLESS = "dimensionless"
    PRIOR = "prior"
    CONSTANT = "constant"


@dataclass(frozen=True)
class Constraint:
    left: DimensionExpr
    right: DimensionExpr
    line: int
    column: int | None = None
    end_column: int | None = None
    kind: ConstraintKind = ConstraintKind.EQUALITY
    message: str = ""
    chain: tuple[str, ...] = ()

    def equation_text(self) -> str:
        return f"{self.left} = {self.right}"