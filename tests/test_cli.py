import json

from rayleigh.cli import main


def test_json_contains_recursive_provenance(
    tmp_path,
    capsys,
) -> None:
    source_file = tmp_path / "example.py"

    source_file.write_text(
        "distance = 100\n"
        "time = 5\n"
        "speed = distance / time\n",
        encoding="utf-8",
    )

    exit_code = main(
        [
            "check",
            str(source_file),
            "--json",
        ]
    )

    assert exit_code == 0

    output = capsys.readouterr().out
    payload = json.loads(output)

    assert payload["status"] == "consistent"
    assert "provenance" in payload
    assert "diagnostics" in payload
    assert payload["diagnostics"] == []

    speed = next(
        item
        for item in payload["provenance"]
        if item["variable"] == "speed"
    )

    assert speed["dimension"] == "L T^-1"

    expression = next(
        item
        for item in speed["evidence"]
        if item["text"] == "speed = distance / time"
    )

    dependencies = expression["dependencies"]

    names = {
        dependency["variable"]
        for dependency in dependencies
    }

    assert names == {"distance", "time"}


def test_consistent_returns_zero(
    tmp_path,
    capsys,
) -> None:
    source_file = tmp_path / "valid.py"

    source_file.write_text(
        "distance = 100\n"
        "time = 5\n"
        "speed = distance / time\n",
        encoding="utf-8",
    )

    exit_code = main(
        [
            "check",
            str(source_file),
        ]
    )

    assert exit_code == 0

    output = capsys.readouterr().out

    assert "✓ CONSISTENT" in output


def test_unknown_returns_zero(
    tmp_path,
    capsys,
) -> None:
    source_file = tmp_path / "unknown.py"

    source_file.write_text(
        "q = external_q\n"
        "u = external_u\n"
        "result = q * u\n",
        encoding="utf-8",
    )

    exit_code = main(
        [
            "check",
            str(source_file),
        ]
    )

    assert exit_code == 0

    output = capsys.readouterr().out

    assert "? UNKNOWN" in output


def test_contradiction_returns_one(
    tmp_path,
    capsys,
) -> None:
    source_file = tmp_path / "invalid.py"

    source_file.write_text(
        "velocity = 10\n"
        "gravity = 9.81\n"
        "bad_value = velocity + gravity\n",
        encoding="utf-8",
    )

    exit_code = main(
        [
            "check",
            str(source_file),
        ]
    )

    assert exit_code == 1

    output = capsys.readouterr().out

    assert "✗ DIMENSIONAL CONTRADICTION" in output


def test_missing_file_returns_two(
    tmp_path,
    capsys,
) -> None:
    source_file = tmp_path / "does_not_exist.py"

    exit_code = main(
        [
            "check",
            str(source_file),
        ]
    )

    assert exit_code == 2

    captured = capsys.readouterr()

    assert "rayleigh:" in captured.err


def test_syntax_error_returns_two(
    tmp_path,
    capsys,
) -> None:
    source_file = tmp_path / "broken.py"

    source_file.write_text(
        "distance =\n",
        encoding="utf-8",
    )

    exit_code = main(
        [
            "check",
            str(source_file),
        ]
    )

    assert exit_code == 2

    captured = capsys.readouterr()

    assert "rayleigh:" in captured.err


def test_json_contradiction_contains_diagnostic(
    tmp_path,
    capsys,
) -> None:
    source_file = tmp_path / "invalid.py"

    source_file.write_text(
        "velocity = 10\n"
        "gravity = 9.81\n"
        "bad_value = velocity + gravity\n",
        encoding="utf-8",
    )

    exit_code = main(
        [
            "check",
            str(source_file),
            "--json",
        ]
    )

    assert exit_code == 1

    payload = json.loads(
        capsys.readouterr().out
    )

    assert payload["status"] == "contradiction"

    assert len(payload["diagnostics"]) == 1

    diagnostic = payload["diagnostics"][0]

    assert diagnostic["code"] == "dimension_mismatch"
    assert diagnostic["severity"] == "error"
    assert diagnostic["line"] == 3

    assert diagnostic["column"] is not None
    assert diagnostic["end_column"] is not None

    assert (
        diagnostic["message"]
        == "addition/subtraction requires matching dimensions"
    )


def test_diagnostic_format_is_editor_friendly(
    tmp_path,
    capsys,
) -> None:
    source_file = tmp_path / "invalid.py"

    source_file.write_text(
        "velocity = 10\n"
        "gravity = 9.81\n"
        "bad_value = velocity + gravity\n",
        encoding="utf-8",
    )

    exit_code = main(
        [
            "check",
            str(source_file),
            "--diagnostic",
        ]
    )

    assert exit_code == 1

    output = capsys.readouterr().out.strip()

    assert str(source_file) in output
    assert ":3:" in output
    assert "error[dimension_mismatch]:" in output
    assert (
        "addition/subtraction requires matching dimensions"
        in output
    ) 