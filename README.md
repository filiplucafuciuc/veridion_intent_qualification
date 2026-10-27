# Intent Qualification System

This project ranks company records against natural-language business queries.
It combines:

1. deterministic parsing and hard-constraint checks;
2. dependency-free TF-IDF candidate retrieval;
3. field-aware evidence scoring and explanations.

The core pipeline does not require an external API or an LLM.

## Requirements

Python 3.10+ and the packages in [`requirements.txt`](requirements.txt).

Install the development dependency:

```bash
python3 -m pip install -r requirements.txt
```

## Run one query

From the project root:

```bash
python3 run.py \
  'Public software companies with more than 1,000 employees.' \
  --limit 10
```

Use `--json` for machine-readable output:

```bash
python3 run.py \
  'Pharmaceutical companies in Switzerland' \
  --limit 5 \
  --json
```

## Reproduce the analysis

```bash
python3 scripts/profile_data.py companies.jsonl
python3 -m scripts.evaluate_structured --limit 10
python3 -m scripts.evaluate_lexical --limit 10
python3 -m scripts.evaluate_hybrid --limit 10 --candidate-limit 100
python3 -m scripts.build_comparison --limit 5
python3 -m scripts.evaluate_objective --report reports/hybrid_baseline.json
python3 -m scripts.evaluate_manual
python3 -m pytest -q tests
```

The generated reports under `reports/` preserve the progression from data
profiling through the structured, lexical, and hybrid stages. See
[`WRITEUP.md`](WRITEUP.md) for design decisions, trade-offs, error analysis,
and limitations.
