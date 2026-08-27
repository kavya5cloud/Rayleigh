from __future__ import annotations
from .report import (
    build_provenance,
    render_constraints,
    render_diagnostics,
    render_result,
)
import argparse
import json
import sys
from pathlib import Path

from .report import (
    build_provenance,
    render_constraints,
    render_result,
)
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
    "--diagnostic",
    action="store_true",
    help="emit editor-friendly diagnostics",
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
        "severity": finding.severity,
        "line": finding.line,
        "column": finding.column,
        "end_column": finding.end_column,
        "message": finding.message,
        "left": finding.left,
        "right": finding.right,
        "chain": list(finding.chain),
    }
def _diagnostic_to_json(
    finding,
) -> dict[str, object]:
    return {
        "line": finding.line,
        "column": (
            finding.column + 1
            if finding.column is not None
            else None
        ),
        "end_column": (
            finding.end_column + 1
            if finding.end_column is not None
            else None
        ),
        "severity": finding.severity,
        "code": finding.kind,
        "message": finding.message,
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
    if args.diagnostic:
        output = render_diagnostics(
            result,
            str(args.file),
        )

        if output:
            print(output)

        return {
            "consistent": 0,
            "contradiction": 1,
            "unknown": 0,
        }[result.status]

    if args.as_json:
        contradictions = []

        if result.contradictions:
            primary = next(
                (
                    finding
                    for finding in result.contradictions
                    if finding.kind == "dimension_mismatch"
                ),
                result.contradictions[0],
            )

            contradictions = [
                _finding_to_json(primary)
            ]

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
            "diagnostics": [
                _diagnostic_to_json(finding)
                for finding in result.contradictions[:1]
            ],
            "contradictions": contradictions,
            "provenance": build_provenance(
                walk,
                result,
            ),
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
                walk,
            )
        )

    return {
        "consistent": 0,
        "contradiction": 1,
        "unknown": 0,
    }[result.status]


if __name__ == "__main__":
    raise SystemExit(main())

def _diagnostic_to_json(
    finding,
) -> dict[str, object]:
    return {
        "line": finding.line,
        "column": (
            finding.column + 1
            if finding.column is not None
            else None
        ),
        "end_column": (
            finding.end_column + 1
            if finding.end_column is not None
            else None
        ),
        "severity": finding.severity,
        "code": finding.kind,
        "message": finding.message,
    }