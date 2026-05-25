"""Validation checks for synthetic admin datasets (last 3 months)."""
from __future__ import annotations

import csv
from datetime import UTC, datetime
from pathlib import Path

BASE = Path("data/synthetic")
MASTER = BASE / "interactions.csv"

if not MASTER.exists():
    raise SystemExit("missing synthetic interactions.csv; run generate_synthetic_admin_data.py first")

rows = list(csv.DictReader(MASTER.open()))
assert rows, "dataset must not be empty"
required = {"interaction_id", "date", "month_bucket", "icp", "pain_area", "duration_min", "score"}
assert required.issubset(rows[0].keys()), f"missing columns: {required - set(rows[0].keys())}"
assert len({r["interaction_id"] for r in rows}) == len(rows), "interaction_id must be unique"

today = datetime.now(UTC).date()
min_allowed = today.replace(day=1)
# subtract 2 months from current month
for _ in range(2):
    y = min_allowed.year
    m = min_allowed.month - 1
    if m == 0:
        y -= 1
        m = 12
    min_allowed = min_allowed.replace(year=y, month=m)

for row in rows:
    d = datetime.fromisoformat(row["date"]).date()
    assert min_allowed <= d <= today, f"date out of last-3-month range: {d}"

monthly_files = sorted(BASE.glob("interactions_*.csv"))
assert len(monthly_files) >= 3, "expected at least 3 month-specific datasets"

print(f"Validation passed for {len(rows)} rows across {len(monthly_files)} monthly datasets")
