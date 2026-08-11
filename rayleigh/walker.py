from __future__ import annotations

import ast
from dataclasses import dataclass
from fractions import Fraction
from typing import Iterable

from .constants import match_constant
from .constraints import Constraint, ConstraintKind
from .dimension import Dimension, DimensionExpr
from .priors import infer_prior


@dataclass
class WalkResult:
    constraints: list[Constraint]
    variables: set[str]


class ConstraintWalker(ast.NodeVisitor):
    """Walk Python AST and emit dimensional constraints without solving them."""

    def __init__(self) -> None:
        self.constraints: list[Constraint] = []
        self.variables: set[str] = set()
        self._node_cache: dict[int, DimensionExpr] = {}

    def analyze(self, tree: ast.AST) -> WalkResult:
        self.visit(tree)
        return WalkResult(self.constraints, self.variables)

    def visit_Assign(self, node: ast.Assign) -> None:
        value = self._expr(node.value)
        for target in node.targets:
            self._bind(target, value, node.lineno)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if node.value is not None:
            value = self._expr(node.value)
            self._bind(node.target, value, node.lineno)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        if isinstance(node.target, ast.Name):
            target = self._name_expr(node.target.id)
            value = self._expr(node.value)
            if isinstance(node.op, (ast.Add, ast.Sub)):
                self._add_equality(target, value, node.lineno, "augmented assignment")
        self.generic_visit(node)

    def visit_Expr(self, node: ast.Expr) -> None:
        self._expr(node.value)

    def visit_If(self, node: ast.If) -> None:
        self._expr(node.test)
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        # V1 intentionally does not infer loop-carried state across iterations.
        self._expr(node.iter)
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        self._expr(node.test)
        self.generic_visit(node)

    def visit_Return(self, node: ast.Return) -> None:
        if node.value is not None:
            self._expr(node.value)

    def _bind(self, target: ast.AST, value: DimensionExpr, line: int) -> None:
        if isinstance(target, ast.Name):
            name = target.id
            self.variables.add(name)
            lhs = self._name_expr(name)
            prior = infer_prior(name)
            if not (prior and self._is_plain_numeric_value(value)):
                self._add_equality(lhs, value, line, f"assignment to {name}")
            if prior:
                dimension, reason = prior
                self._add_equality(lhs, DimensionExpr.concrete(dimension), line, reason, ConstraintKind.PRIOR)
        elif isinstance(target, (ast.Tuple, ast.List)) and isinstance(value, DimensionExpr):
            # V1 records no destructuring semantics; recurse only when RHS itself is handled elsewhere.
            for elt in target.elts:
                if isinstance(elt, ast.Name):
                    self.variables.add(elt.id)

    def _expr(self, node: ast.AST) -> DimensionExpr:
        cached = self._node_cache.get(id(node))
        if cached is not None:
            return cached

        result: DimensionExpr
        if isinstance(node, ast.Name):
            self.variables.add(node.id)
            result = self._name_expr(node.id)
        elif isinstance(node, ast.Constant):
            result = self._constant_expr(node)
        elif isinstance(node, ast.UnaryOp):
            result = self._expr(node.operand)
        elif isinstance(node, ast.BinOp):
            result = self._binop(node)
        elif isinstance(node, ast.Compare):
            left = self._expr(node.left)
            for comparator in node.comparators:
                right = self._expr(comparator)
                self._add_equality(left, right, getattr(node, "lineno", 0), "comparison")
                left = right
            result = DimensionExpr.dimensionless()
        elif isinstance(node, ast.BoolOp):
            for value in node.values:
                self._expr(value)
            result = DimensionExpr.dimensionless()
        elif isinstance(node, ast.Call):
            result = self._call(node)
        elif isinstance(node, ast.IfExp):
            self._expr(node.test)
            left = self._expr(node.body)
            right = self._expr(node.orelse)
            self._add_equality(left, right, getattr(node, "lineno", 0), "conditional expression")
            result = left
        elif isinstance(node, ast.Attribute):
            # Cross-module attribute inference is explicitly out of scope for V1.
            result = DimensionExpr.unknown(ast.unparse(node))
        elif isinstance(node, (ast.List, ast.Tuple, ast.Set, ast.Dict)):
            for child in ast.iter_child_nodes(node):
                if isinstance(child, ast.expr):
                    self._expr(child)
            result = DimensionExpr.dimensionless()
        else:
            for child in ast.iter_child_nodes(node):
                if isinstance(child, ast.expr):
                    self._expr(child)
            result = DimensionExpr.unknown(f"expr@{getattr(node, 'lineno', 0)}")

        self._node_cache[id(node)] = result
        return result

    def _binop(self, node: ast.BinOp) -> DimensionExpr:
        left = self._expr(node.left)
        right = self._expr(node.right)
        line = getattr(node, "lineno", 0)
        if isinstance(node.op, (ast.Add, ast.Sub)):
            self._add_equality(
                left,
                right,
                line,
                "addition/subtraction",
                chain=(
                    "both operands must have equal dimensions",
                ),
            )
            return left
        if isinstance(node.op, ast.Mult):
            return left + right
        if isinstance(node.op, ast.Div):
            return left - right
        if isinstance(node.op, ast.Pow):
            exponent = self._numeric_value(node.right)
            if exponent is None:
                self._add_equality(right, DimensionExpr.dimensionless(), line, "power exponent must be dimensionless")
                return DimensionExpr.unknown(f"pow@{line}")
            return left.scale(exponent)
        if isinstance(node.op, ast.Mod):
            self._add_equality(left, right, line, "modulo")
            return left
        # Floor division has the same dimensional algebra as division for V1.
        if isinstance(node.op, ast.FloorDiv):
            return left - right
        return DimensionExpr.unknown(f"binop@{line}")

    def _call(self, node: ast.Call) -> DimensionExpr:
        name = self._call_name(node.func)
        args = [self._expr(arg) for arg in node.args]
        line = getattr(node, "lineno", 0)
        if name in {"sin", "cos", "tan", "asin", "acos", "atan", "exp", "log", "log10", "sqrt"}:
            if args:
                if name == "sqrt":
                    return args[0].scale(Fraction(1, 2))
                self._add_equality(args[0], DimensionExpr.dimensionless(), line, f"{name} argument")
            return DimensionExpr.dimensionless()
        if name in {"abs", "fabs"} and args:
            return args[0]
        if name in {"min", "max"} and args:
            for arg in args[1:]:
                self._add_equality(args[0], arg, line, f"{name} arguments")
            return args[0]
        return DimensionExpr.unknown(f"call:{name or '<call>'}@{line}")

    @staticmethod
    def _is_plain_numeric_value(value: DimensionExpr) -> bool:
        return (
            value.constant.is_dimensionless()
            and not value.coefficients
        )

    def _constant_expr(self, node: ast.Constant) -> DimensionExpr:
        if isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            fingerprint = match_constant(float(node.value))
            if fingerprint:
                self.constraints.append(
                    Constraint(
                        left=DimensionExpr.unknown(f"const:{node.value}"),
                        right=DimensionExpr.concrete(fingerprint.dimension),
                        line=getattr(node, "lineno", 0),
                        kind=ConstraintKind.CONSTANT,
                        message=f"recognized constant {fingerprint.name}",
                        chain=(
                            f"{node.value} ≈ {fingerprint.name}",
                            f"{fingerprint.name} → {fingerprint.dimension.format()}",
                        ),
                    )
                )
                return DimensionExpr.unknown(f"const:{node.value}")
            return DimensionExpr.dimensionless()
        if isinstance(node.value, complex):
            return DimensionExpr.dimensionless()
        if node.value is None or isinstance(node.value, bool):
            return DimensionExpr.dimensionless()
        return DimensionExpr.unknown(f"literal@{getattr(node, 'lineno', 0)}")

    def _name_expr(self, name: str) -> DimensionExpr:
        return DimensionExpr.unknown(f"var:{name}")

    def _add_equality(
        self,
        left: DimensionExpr,
        right: DimensionExpr,
        line: int,
        message: str,
        kind: ConstraintKind = ConstraintKind.EQUALITY,
        chain: tuple[str, ...] | None = None,
    ) -> None:
        self.constraints.append(
            Constraint(
                left=left,
                right=right,
                line=line,
                kind=kind,
                message=message,
                chain=chain or (message,),
        )
    )

    @staticmethod
    def _numeric_value(node: ast.AST) -> Fraction | None:
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return Fraction(str(node.value))
        if isinstance(node, ast.UnaryOp) and isinstance(node.operand, ast.Constant):
            if isinstance(node.operand.value, (int, float)) and not isinstance(node.operand.value, bool):
                value = Fraction(str(node.operand.value))
                if isinstance(node.op, ast.USub):
                    return -value
                if isinstance(node.op, ast.UAdd):
                    return value
        return None

    @staticmethod
    def _call_name(node: ast.AST) -> str | None:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return node.attr
        return None


def collect_constraints(source: str, filename: str = "<string>") -> WalkResult:
    tree = ast.parse(source, filename=filename)
    return ConstraintWalker().analyze(tree)
