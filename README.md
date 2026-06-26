# HireIQ Dev A Ranking Pipeline

Run the judged ranking path with:

```bash
python rank.py --candidates ./datasets/candidates.jsonl --out ./submission.csv
```

For local validation:

```bash
python validate_output.py submission.csv
```

The pipeline streams `.json`, `.jsonl`, and `.jsonl.gz` inputs, keeps only a
top-200 heap in memory, and writes exactly 100 ranked rows in the required CSV
format. It reads `precomputed/reasoning_map.json` when Dev B has generated it;
otherwise it falls back to deterministic candidate-specific reasoning.
