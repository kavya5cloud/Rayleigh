from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .report import render_constraints, render_result
from .solver import solve
from .walker import collect_constraints


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rayleigh", description="Infer dimensions and detect dimensional inconsistencies in Python code.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    check = subparsers.add_parser("check", help="check a Python source file")
    check.add_argument("file", type=Path)
    check.add_argument("--constraints", action="store_true", help="print collected constraints before solving")
    check.add_argument("--json", action="store_true", dest="as_json", help="emit machine-readable JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command != "check":
        return 2
    try:
        source = args.file.read_text(encoding="utf-8")
        walk = collect_constraints(source, str(args.file))
    except (OSError, SyntaxError) as exc:
        print(f"rayleigh: {exc}", file=sys.stderr)
        return 2

    if args.constraints:
        print(render_constraints(walk))
        print()

    result = solve(walk.constraints)
    if args.as_json:
        payload = {
            "status": result.status,
            "assignments": {
                name: (dim.exponents if dim is not None else None)
                for name, dim in result.assignments.items()
            },
            "unknowns": sorted(result.unknowns),
            "contradictions": [
                {
                    "line": f.line,
                    "message": f.message,
                    "left": f.left,
                    "right": f.right,
                    "chain": list(f.chain),
                }
                for f in result.contradictions
            ],
        }
        print(json.dumps(payload, default=str, indent=2))
    else:
        print(render_result(result))

    return {"consistent": 0, "contradiction": 1, "unknown": 0}[result.status]


if __name__ == "__main__":
    raise SystemExit(main())
