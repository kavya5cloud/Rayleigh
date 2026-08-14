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