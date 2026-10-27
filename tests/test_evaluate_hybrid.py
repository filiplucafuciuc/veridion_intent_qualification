import json
from pathlib import Path

from scripts.evaluate_hybrid import main


def test_hybrid_report_contains_scores_and_decisions(tmp_path, monkeypatch):
    output = tmp_path / "hybrid.json"
    monkeypatch.setattr(
        "sys.argv",
        ["evaluate_hybrid", "--output", str(output), "--limit", "3"],
    )

    main()

    report = json.loads(output.read_text(encoding="utf-8"))
    assert len(report) == 12
    assert all(len(item["results"]) == 3 for item in report)
    assert all("final_score" in item["results"][0] for item in report)
