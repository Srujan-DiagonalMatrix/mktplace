"""Generate synthetic datasets for admin analytics validation/demo."""
from __future__ import annotations
import csv, random, uuid
from datetime import datetime, timedelta
from pathlib import Path

OUT = Path("data/synthetic")
OUT.mkdir(parents=True, exist_ok=True)

icps = ["Family", "Student", "Business", "Couple", "Large Family", "Low Income"]
pains = ["Financing", "Budget", "Right Vehicle", "Economy", "Availability"]
start = datetime.utcnow() - timedelta(days=90)

with (OUT / "interactions.csv").open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["interaction_id", "date", "icp", "pain_area", "duration_min", "score"])
    w.writeheader()
    for _ in range(1000):
        w.writerow({
            "interaction_id": str(uuid.uuid4()),
            "date": (start + timedelta(days=random.randint(0, 90))).date().isoformat(),
            "icp": random.choice(icps),
            "pain_area": random.choice(pains),
            "duration_min": random.randint(2, 40),
            "score": round(random.uniform(-1, 1), 2),
        })

print(f"Synthetic dataset written to {OUT}")
