"""Validation checks for synthetic admin dataset."""
from __future__ import annotations
import csv
from pathlib import Path

p = Path("data/synthetic/interactions.csv")
if not p.exists():
    raise SystemExit("missing synthetic interactions.csv; run generate_synthetic_admin_data.py first")

rows = list(csv.DictReader(p.open()))
assert rows, "dataset must not be empty"
required = {"interaction_id", "date", "icp", "pain_area", "duration_min", "score"}
assert required.issubset(rows[0].keys()), f"missing columns: {required - set(rows[0].keys())}"
assert len({r['interaction_id'] for r in rows}) == len(rows), "interaction_id must be unique"
print(f"Validation passed for {len(rows)} rows")
