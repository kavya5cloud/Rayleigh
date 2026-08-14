from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .report import render_constraints, render_result
from .solver import solve
from .walker import collect_constraints


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rayleigh",
        description=(
            "Infer dimensions and detect dimensional "
            "inconsistencies in Python code."
        ),
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    check = subparsers.add_parser(
        "check",
        help="check a Python source file",
    )

    check.add_argument(
        "file",
        type=Path,
    )

    check.add_argument(
        "--constraints",
        action="store_true",
        help="print collected constraints before solving",
    )

    check.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="emit machine-readable JSON",
    )

    return parser


def _dimension_to_json(dimension) -> list[str] | None:
    if dimension is None:
        return None

    return [
        str(exponent)
        for exponent in dimension.exponents
    ]


def _finding_to_json(finding) -> dict[str, object]:
    return {
        "kind": finding.kind,
        "line": finding.line,
        "message": finding.message,
        "left": finding.left,
        "right": finding.right,
        "chain": list(finding.chain),
    }

def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command != "check":
        return 2

    try:
        source = args.file.read_text(
            encoding="utf-8",
        )

        walk = collect_constraints(
            source,
            str(args.file),
        )

    except (OSError, SyntaxError) as exc:
        print(
            f"rayleigh: {exc}",
            file=sys.stderr,
        )
        return 2

    result = solve(walk.constraints)

    if args.as_json:
        payload = {
            "tool": "rayleigh",
            "status": result.status,
            "file": str(args.file),
            "assignments": {
                name: _dimension_to_json(dimension)
                for name, dimension
                in sorted(result.assignments.items())
            },
            "unknowns": sorted(result.unknowns),
            "contradictions": [
             _finding_to_json(
            next(
                (
                    finding
                    for finding in result.contradictions
                    if finding.kind == "dimension_mismatch"
                ),
            result.contradictions[0],
        )
    )
] if result.contradictions else [],
        }

        print(
            json.dumps(
                payload,
                indent=2,
                sort_keys=True,
            )
        )

    else:
        if args.constraints:
            print(render_constraints(walk))
            print()

        print(
            render_result(
                result,
                source,
            )
        )

    return {
        "consistent": 0,
        "contradiction": 1,
        "unknown": 0,
    }[result.status]


if __name__ == "__main__":
    raise SystemExit(main())