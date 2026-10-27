import json
from pathlib import Path

from scripts.evaluate_objective import main


def test_objective_report_counts_hard_violations(tmp_path, monkeypatch, capsys):
    report = [
        {
            "query": "example",
            "results": [
                {
                    "name": "Wrong",
                    "decision": "match",
                    "violated_constraints": ["location"],
                }
            ],
        }
    ]
    path = tmp_path / "report.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["evaluate_objective", "--report", str(path)])

    main()

    assert "match_with_hard_violations=1" in capsys.readouterr().out
