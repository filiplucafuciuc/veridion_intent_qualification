import json
from pathlib import Path

from scripts.evaluate_lexical import main


def test_lexical_report_contains_all_queries(tmp_path, monkeypatch):
    output = tmp_path / "lexical.json"
    monkeypatch.setattr(
        "sys.argv",
        ["evaluate_lexical", "--output", str(output), "--limit", "3"],
    )

    main()

    report = json.loads(output.read_text(encoding="utf-8"))
    assert len(report) == 12
    assert all(len(item["results"]) == 3 for item in report)
