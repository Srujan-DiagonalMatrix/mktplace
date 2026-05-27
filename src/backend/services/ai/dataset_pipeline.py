from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REQUIRED_DATASETS: dict[str, str] = {
    "conversation_turns": "conversation_turns.jsonl",
    "preference_ground_truth": "preference_ground_truth.csv",
    "dialogue_policy_labels": "dialogue_policy_labels.jsonl",
    "llm_prompt_eval": "llm_prompt_eval.jsonl",
    "vehicle_attribute_ontology": "vehicle_attribute_ontology.csv",
    "conversation_outcomes": "conversation_outcomes.csv",
    "safety_cases": "safety_cases.jsonl",
    "labeling_guide": "labeling_guide.md",
}


@dataclass(frozen=True)
class DataQualityReport:
    rows_by_dataset: dict[str, int]
    duplicates: dict[str, int]
    missing_required_fields: dict[str, int]


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def validate_dataset_inventory(base_dir: Path | str) -> dict[str, Path]:
    root = Path(base_dir)
    missing = [filename for filename in REQUIRED_DATASETS.values() if not (root / filename).exists()]
    if missing:
        raise FileNotFoundError(f"Missing required dataset files: {missing}")
    return {name: (root / filename) for name, filename in REQUIRED_DATASETS.items()}


def normalize_nulls(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    null_tokens = {"", "null", "none", "n/a", "na"}
    for row in rows:
        normalized_row: dict[str, Any] = {}
        for key, value in row.items():
            if isinstance(value, str) and value.strip().lower() in null_tokens:
                normalized_row[key] = None
            else:
                normalized_row[key] = value
        normalized.append(normalized_row)
    return normalized


def canonicalize_preference_row(
    row: dict[str, Any],
    ontology_rows: list[dict[str, str]],
) -> dict[str, Any]:
    alias_to_canonical: dict[tuple[str, str], str] = {}
    for onto in ontology_rows:
        attribute = (onto.get("attribute") or "").strip()
        canonical = (onto.get("canonical_value") or "").strip()
        aliases = (onto.get("aliases") or "").split("|")
        alias_to_canonical[(attribute, canonical.lower())] = canonical
        for alias in aliases:
            alias_to_canonical[(attribute, alias.strip().lower())] = canonical

    out = dict(row)
    for key in ("fuel_type", "transmission", "body_type", "employment_status"):
        value = out.get(key)
        if isinstance(value, str) and value.strip():
            mapped = alias_to_canonical.get((key, value.strip().lower()))
            if mapped:
                out[key] = mapped
    return out


def split_by_conversation(rows: list[dict[str, Any]], train_ratio: float = 0.8) -> dict[str, list[dict[str, Any]]]:
    conv_ids = sorted({str(r.get("conversation_id")) for r in rows if r.get("conversation_id")})
    if not conv_ids:
        return {"train": [], "test": []}
    train_cutoff = max(1, int(len(conv_ids) * train_ratio))
    train_ids = set(conv_ids[:train_cutoff])
    train = [r for r in rows if str(r.get("conversation_id")) in train_ids]
    test = [r for r in rows if str(r.get("conversation_id")) not in train_ids]
    return {"train": train, "test": test}


def build_data_quality_report(base_dir: Path | str) -> DataQualityReport:
    inventory = validate_dataset_inventory(base_dir)
    rows_by_dataset: dict[str, int] = {}
    duplicates: dict[str, int] = {}
    missing_required_fields: dict[str, int] = {}

    for name, path in inventory.items():
        if path.suffix == ".jsonl":
            rows = _read_jsonl(path)
        elif path.suffix == ".csv":
            rows = _read_csv(path)
        else:
            continue
        rows = normalize_nulls(rows)
        rows_by_dataset[name] = len(rows)
        seen = set()
        dupes = 0
        missing = 0
        for row in rows:
            marker = json.dumps(row, sort_keys=True, default=str)
            if marker in seen:
                dupes += 1
            seen.add(marker)
            if any(v is None for v in row.values()):
                missing += 1
        duplicates[name] = dupes
        missing_required_fields[name] = missing

    return DataQualityReport(
        rows_by_dataset=rows_by_dataset,
        duplicates=duplicates,
        missing_required_fields=missing_required_fields,
    )

