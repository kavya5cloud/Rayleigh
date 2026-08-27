from __future__ import annotations

import json
import re
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).parent
MANIFEST = ROOT / "MANIFEST.json"

VALID_STATUSES = {
    "consistent",
    "contradiction",
    "unknown",
}

EXPECTED_BY_CATEGORY = {
    "valid": "consistent",
    "invalid": "contradiction",
    "ambiguous": "unknown",
}

REQUIRED_METADATA = {
    "domain",
    "expected",
    "purpose",
}


@dataclass
class BenchmarkResult:
    name: str
    expected: str
    actual: str
    passed: bool
    domain: str


def parse_expected_marker(path: Path) -> str | None:
    """Read an explicit '# EXPECTED: <status>' marker."""
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        return None

    for line in source.splitlines():
        match = re.match(
            r"\s*#\s*EXPECTED:\s*(\w+)\s*$",
            line,
            re.IGNORECASE,
        )

        if not match:
            continue

        status = match.group(1).lower()

        if status in VALID_STATUSES:
            return status

    return None


def discover_cases() -> list[Path]:
    """Discover all benchmark Python files."""
    cases: list[Path] = []

    for category in (
        "valid",
        "invalid",
        "ambiguous",
    ):
        directory = ROOT / category

        if directory.exists():
            cases.extend(
                directory.glob("*.py")
            )

    domain = ROOT / "domain"

    if domain.exists():
        cases.extend(
            domain.rglob("*.py")
        )

    return sorted(cases)


def infer_expected_from_path(
    path: Path,
) -> str | None:
    """Infer expected status for legacy benchmark categories."""
    relative = path.relative_to(ROOT)
    parts = relative.parts

    if not parts:
        return None

    return EXPECTED_BY_CATEGORY.get(parts[0])


def infer_domain_from_path(path: Path) -> str:
    """Infer a readable domain name from a benchmark path."""
    relative = path.relative_to(ROOT)
    parts = relative.parts

    if not parts:
        return "unknown"

    if parts[0] == "domain" and len(parts) >= 2:
        return parts[1]

    return "core"


def build_default_manifest() -> dict:
    """Build a manifest from the current benchmark tree."""
    cases: dict[str, dict[str, str]] = {}

    for path in discover_cases():
        relative = str(
            path.relative_to(ROOT)
        )

        expected = infer_expected_from_path(path)

        if expected is None:
            expected = parse_expected_marker(path)

        if expected is None:
            raise SystemExit(
                f"Missing expected status for {relative}"
            )

        cases[relative] = {
            "domain": infer_domain_from_path(path),
            "expected": expected,
            "purpose": (
                path.stem
                .replace("_", " ")
                .strip()
            ),
        }

    return {
        "version": 1,
        "description": (
            "Rayleigh dimensional-analysis "
            "benchmark suite"
        ),
        "cases": cases,
    }


def load_manifest() -> dict:
    """Load the benchmark manifest, generating it if needed."""
    if not MANIFEST.exists():
        manifest = build_default_manifest()

        MANIFEST.write_text(
            json.dumps(
                manifest,
                indent=2,
                sort_keys=True,
            ) + "\n",
            encoding="utf-8",
        )

        return manifest

    try:
        manifest = json.loads(
            MANIFEST.read_text(
                encoding="utf-8",
            )
        )
    except (
        OSError,
        json.JSONDecodeError,
    ) as exc:
        raise SystemExit(
            f"Invalid benchmark manifest: {exc}"
        ) from exc

    if not isinstance(manifest, dict):
        raise SystemExit(
            "Benchmark manifest must be an object"
        )

    cases = manifest.get("cases")

    if cases == {}:
        manifest = build_default_manifest()

        MANIFEST.write_text(
            json.dumps(
                manifest,
                indent=2,
                sort_keys=True,
            ) + "\n",
            encoding="utf-8",
        )

        return manifest

    if not isinstance(cases, dict):
        raise SystemExit(
            "Benchmark manifest must contain "
            "a 'cases' object"
        )

    return manifest


def validate_manifest(manifest: dict) -> None:
    """Ensure manifest and benchmark tree are synchronized."""
    cases = manifest["cases"]

    discovered = {
        str(path.relative_to(ROOT))
        for path in discover_cases()
    }

    manifest_paths = set(cases)

    missing = discovered - manifest_paths
    stale = manifest_paths - discovered

    if missing:
        raise SystemExit(
            "Manifest missing cases:\n"
            + "\n".join(
                f"  - {path}"
                for path in sorted(missing)
            )
        )

    if stale:
        raise SystemExit(
            "Manifest contains missing files:\n"
            + "\n".join(
                f"  - {path}"
                for path in sorted(stale)
            )
        )

    for path, metadata in cases.items():
        if not isinstance(metadata, dict):
            raise SystemExit(
                f"Invalid metadata for {path}"
            )

        missing_metadata = (
            REQUIRED_METADATA
            - set(metadata)
        )

        if missing_metadata:
            raise SystemExit(
                f"Missing metadata for {path}: "
                + ", ".join(
                    sorted(missing_metadata)
                )
            )

        expected = metadata.get("expected")
        domain = metadata.get("domain")
        purpose = metadata.get("purpose")

        if expected not in VALID_STATUSES:
            raise SystemExit(
                f"Invalid expected status for {path}: "
                f"{expected!r}"
            )

        if not isinstance(domain, str) or not domain:
            raise SystemExit(
                f"Missing domain for {path}"
            )

        if not isinstance(purpose, str) or not purpose:
            raise SystemExit(
                f"Missing purpose for {path}"
            )


def detect_actual(output: str) -> str:
    """Convert Rayleigh CLI output into a status."""
    if "✓ CONSISTENT" in output:
        return "consistent"

    if "✗ DIMENSIONAL CONTRADICTION" in output:
        return "contradiction"

    if "? UNKNOWN" in output:
        return "unknown"

    return "error"


def run_case(
    path: Path,
    expected: str,
    domain: str,
) -> BenchmarkResult:
    """Run one benchmark case."""
    result = subprocess.run(
        [
            "rayleigh",
            "check",
            str(path),
        ],
        capture_output=True,
        text=True,
    )

    output = result.stdout + result.stderr
    actual = detect_actual(output)

    return BenchmarkResult(
        name=str(path.relative_to(ROOT)),
        expected=expected,
        actual=actual,
        passed=actual == expected,
        domain=domain,
    )


def print_summary(
    results: list[BenchmarkResult],
) -> None:
    """Print domain and status summaries."""
    print()
    print("Benchmark Summary")
    print("-" * 72)

    # ------------------------------------------------------------
    # Results by domain.
    # ------------------------------------------------------------

    by_domain: dict[
        str,
        list[BenchmarkResult],
    ] = defaultdict(list)

    for result in results:
        by_domain[result.domain].append(result)

    for domain in sorted(by_domain):
        domain_results = by_domain[domain]
        passed = sum(
            result.passed
            for result in domain_results
        )
        total = len(domain_results)

        percentage = (
            passed / total * 100
            if total
            else 0.0
        )

        print(
            f"{domain.title():20} "
            f"{passed:2}/{total:<2} "
            f"({percentage:5.1f}%)"
        )

    # ------------------------------------------------------------
    # Results by actual status.
    # ------------------------------------------------------------

    status_counts = Counter(
        result.actual
        for result in results
    )

    print()
    print("Status Distribution")
    print("-" * 72)

    for status in (
        "consistent",
        "contradiction",
        "unknown",
        "error",
    ):
        print(
            f"{status.title():20} "
            f"{status_counts.get(status, 0)}"
        )


def main() -> None:
    manifest = load_manifest()
    validate_manifest(manifest)

    results: list[BenchmarkResult] = []

    for relative, metadata in sorted(
        manifest["cases"].items()
    ):
        path = ROOT / relative

        results.append(
            run_case(
                path,
                metadata["expected"],
                metadata["domain"],
            )
        )

    print("Rayleigh Benchmark")
    print("=" * 72)

    for result in results:
        status = (
            "PASS"
            if result.passed
            else "FAIL"
        )

        print(
            f"{status:5} "
            f"{result.name:55} "
            f"expected={result.expected:13} "
            f"actual={result.actual}"
        )

    passed = sum(
        result.passed
        for result in results
    )
    total = len(results)

    print("=" * 72)
    print(f"Passed: {passed}/{total}")

    if total:
        accuracy = (
            passed / total * 100
        )

        print(
            f"Accuracy: {accuracy:.1f}%"
        )

    print_summary(results)

    if passed != total:
        raise SystemExit(1)


if __name__ == "__main__":
    main()