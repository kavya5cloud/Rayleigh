from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess


ROOT = Path(__file__).parent


@dataclass
class BenchmarkResult:
    name: str
    expected: str
    actual: str
    passed: bool


EXPECTED = {
    "valid": "consistent",
    "invalid": "contradiction",
    "ambiguous": "unknown",
}


def run_case(path: Path, expected: str) -> BenchmarkResult:
    result = subprocess.run(
        ["rayleigh", "check", str(path)],
        capture_output=True,
        text=True,
    )

    output = result.stdout + result.stderr

    if "✓ CONSISTENT" in output:
        actual = "consistent"
    elif "✗ DIMENSIONAL CONTRADICTION" in output:
        actual = "contradiction"
    elif "? UNKNOWN" in output:
        actual = "unknown"
    else:
        actual = "error"

    return BenchmarkResult(
        name=str(path.relative_to(ROOT)),
        expected=expected,
        actual=actual,
        passed=actual == expected,
    )


def main() -> None:
    results: list[BenchmarkResult] = []

    # Original benchmark categories.
    for category, expected in EXPECTED.items():
        directory = ROOT / category

        for path in sorted(directory.glob("*.py")):
            results.append(
                run_case(path, expected)
            )

    # Domain benchmark categories.
    domain_directory = ROOT / "domain"

    if domain_directory.exists():
        for path in sorted(domain_directory.rglob("*.py")):
            results.append(
                run_case(path, "consistent")
            )

    print("Rayleigh Benchmark")
    print("=" * 72)

    for result in results:
        status = "PASS" if result.passed else "FAIL"

        print(
            f"{status:5} "
            f"{result.name:45} "
            f"expected={result.expected:13} "
            f"actual={result.actual}"
        )

    passed = sum(result.passed for result in results)
    total = len(results)

    print("=" * 72)
    print(f"Passed: {passed}/{total}")

    if total:
        accuracy = passed / total * 100
        print(f"Accuracy: {accuracy:.1f}%")

    if passed != total:
        raise SystemExit(1)


if __name__ == "__main__":
    main()