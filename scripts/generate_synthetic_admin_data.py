"""Generate synthetic datasets for admin analytics validation/demo (last 3 months)."""
from __future__ import annotations

import csv
import random
import uuid
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

OUT = Path("data/synthetic")
OUT.mkdir(parents=True, exist_ok=True)

ICPS = ["Family", "Student", "Business", "Couple", "Large Family", "Low Income"]
PAINS = ["Financing", "Budget", "Right Vehicle", "Economy", "Availability"]


def _first_day_of_month(d: date) -> date:
    return d.replace(day=1)


def _shift_month_start(d: date, months_back: int) -> date:
    y = d.year
    m = d.month - months_back
    while m <= 0:
        m += 12
        y -= 1
    return date(y, m, 1)


def _month_ranges(today: date) -> list[tuple[date, date]]:
    ranges: list[tuple[date, date]] = []
    for n in (2, 1, 0):
        start = _shift_month_start(today, n)
        if n == 0:
            end = today
        else:
            next_month = _shift_month_start(today, n - 1)
            end = next_month - timedelta(days=1)
        ranges.append((start, end))
    return ranges


def _random_row(interaction_date: date) -> dict[str, str | int | float]:
    return {
        "interaction_id": str(uuid.uuid4()),
        "date": interaction_date.isoformat(),
        "month_bucket": interaction_date.strftime("%Y-%m"),
        "icp": random.choice(ICPS),
        "pain_area": random.choice(PAINS),
        "duration_min": random.randint(2, 40),
        "score": round(random.uniform(-1, 1), 2),
    }


def _write_csv(path: Path, rows: list[dict[str, str | int | float]]) -> None:
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["interaction_id", "date", "month_bucket", "icp", "pain_area", "duration_min", "score"],
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    today = datetime.now(UTC).date()
    ranges = _month_ranges(today)

    combined: list[dict[str, str | int | float]] = []
    rows_per_month = 350

    for start, end in ranges:
        days = max((end - start).days, 0)
        month_rows = [_random_row(start + timedelta(days=random.randint(0, days))) for _ in range(rows_per_month)]
        combined.extend(month_rows)
        monthly_name = f"interactions_{start.strftime('%Y_%m')}.csv"
        _write_csv(OUT / monthly_name, month_rows)

    _write_csv(OUT / "interactions.csv", combined)
    print(f"Synthetic datasets written to {OUT} for the last 3 months ({len(combined)} rows total).")


if __name__ == "__main__":
    main()
