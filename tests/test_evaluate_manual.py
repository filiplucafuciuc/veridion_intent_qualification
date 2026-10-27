import json
from pathlib import Path

from scripts.evaluate_manual import main


def test_manual_evaluation_reports_reviewed_count(tmp_path, monkeypatch, capsys):
    path = tmp_path / "reviews.json"
    path.write_text(json.dumps({"reviews": [{"query": "q", "label": 2}]}))
    monkeypatch.setattr("sys.argv", ["evaluate_manual", "--reviews", str(path)])

    main()

    assert "reviewed=1" in capsys.readouterr().out
